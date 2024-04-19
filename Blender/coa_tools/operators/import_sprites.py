'''
Copyright (C) 2015 Andreas Esau
andreasesau@gmail.com

Created by Andreas Esau

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
    
import bpy
import bpy_extras
import bpy_extras.view3d_utils
from math import radians
import mathutils
from mathutils import Vector, Matrix, Quaternion
import math
import bmesh
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
import os
from bpy_extras.io_utils import ExportHelper, ImportHelper
import json
from bpy.app.handlers import persistent
from .. import functions
from .. import constants as CONSTANTS


class COATOOLS_UL_JsonImport(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        
        row.prop(item,"active",text="")
        row.label(text=item.name)

class JsonImportData(bpy.types.PropertyGroup):
    name: StringProperty()
    active: BoolProperty()

class COATOOLS_OT_CreateMaterialGroup(bpy.types.Operator):
    bl_idname = "coa_tools.create_material_group"
    bl_label = "Create COA Tools Node Group"
    bl_description = "Creates the default COA Tools Node Group"
    bl_options = {"REGISTER"}

    input_sockets = [
        {"type": "NodeSocketColor", "label": "Texture Color"},
        {"type": "NodeSocketFloat", "label": "Texture Alpha", "min_value": 0.0, "max_value": 1.0},
        {"type": "NodeSocketColor", "label": "Modulate Color"},
        {"type": "NodeSocketFloat", "label": "Alpha", "min_value": 0.0, "max_value": 1.0},
    ]
    output_sockets = [
        {"type": "NodeSocketShader", "label": "BSDF"},
    ]

    @classmethod
    def poll(cls, context):
        return True

    def create_sockets(self, group_tree):
        inputs = []
        for input_socket in self.input_sockets:
            inputs.append(input_socket["label"])
            socket = group_tree.interface.new_socket(input_socket["label"], description="", in_out="INPUT",socket_type=input_socket["type"])

            if "min_value" in input_socket:
                socket.min_value = input_socket["min_value"]
            if "max_value" in input_socket:
                socket.max_value = input_socket["max_value"]

        outputs = []
        for output_socket in self.output_sockets:
            outputs.append(output_socket["label"])
            socket = group_tree.interface.new_socket(output_socket["label"], description="", in_out="OUTPUT",socket_type=output_socket["type"])
            if "min_value" in output_socket:
                socket.min_value = output_socket["min_value"]
            if "max_value" in output_socket:
                socket.max = output_socket["max_value"]

        for socket in group_tree.interface.items_tree:
            if socket.name not in inputs and socket.in_out == "INPUT":
                group_tree.interface.remove(socket)
            elif socket.name not in outputs and socket.in_out == "OUTPUT":
                group_tree.interface.remove(socket)

    def create_coa_material_group(self):
        group_tree = None

        # cleanup group if already existent
        if CONSTANTS.COA_NODE_GROUP_NAME in bpy.data.node_groups:
            group_tree = bpy.data.node_groups[CONSTANTS.COA_NODE_GROUP_NAME]
            for node in group_tree.nodes:
                group_tree.nodes.remove(node)
        else:
            group_tree = bpy.data.node_groups.new(CONSTANTS.COA_NODE_GROUP_NAME, "ShaderNodeTree")
        # recreate group from scratch to ensure to be always latest version

        # create input/output sockets
        self.create_sockets(group_tree)

        # create nodes
        input_node = group_tree.nodes.new("NodeGroupInput")
        output_node = group_tree.nodes.new("NodeGroupOutput")
        principled_node = group_tree.nodes.new("ShaderNodeBsdfPrincipled")
        modulate_node = group_tree.nodes.new("ShaderNodeMixRGB")
        modulate_node.blend_type = "MULTIPLY"
        modulate_node.inputs[0].default_value = 1.0
        modulate_node.inputs[1].default_value = [1, 1, 1, 1]
        modulate_node.inputs[2].default_value = [1, 1, 1, 1]
        alpha_node = group_tree.nodes.new("ShaderNodeMath")
        alpha_node.operation = "MULTIPLY"
        alpha_node.inputs[0].default_value = 1.0
        alpha_node.inputs[1].default_value = 1.0

        # link node sockets
        group_tree.links.new(input_node.outputs["Modulate Color"], modulate_node.inputs["Color2"])
        group_tree.links.new(input_node.outputs["Alpha"], alpha_node.inputs[1])

        group_tree.links.new(input_node.outputs["Texture Color"], modulate_node.inputs["Color1"])
        group_tree.links.new(modulate_node.outputs["Color"], principled_node.inputs["Base Color"])
        group_tree.links.new(modulate_node.outputs["Color"], principled_node.inputs["Emission Color"])

        group_tree.links.new(input_node.outputs["Texture Alpha"], alpha_node.inputs[0])
        group_tree.links.new(alpha_node.outputs[0], principled_node.inputs["Alpha"])
        group_tree.links.new(principled_node.outputs["BSDF"], output_node.inputs["BSDF"])

        # setup principled node
        principled_node.inputs["Specular IOR Level"].default_value = 0
        principled_node.inputs["Roughness"].default_value = 0
        principled_node.inputs["Coat Roughness"].default_value = 0

        # position nodes
        input_node.location = [0, 0]
        modulate_node.location = [180, 0]
        alpha_node.location = [180, -200]
        principled_node.location = [360, 0]
        output_node.location = [640, 0]

        return group_tree
    
    def execute(self, context):
        self.create_coa_material_group()
        return {"FINISHED"}

class COATOOLS_OT_LoadJsonData(bpy.types.Operator):
    bl_idname = "coa_tools.load_json_data"
    bl_label = "Load Json Data"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    def toggle_active(self,context):
        for item in self.json_import_data:
            item.active = self.active_all
    
    filepath: StringProperty()
    json_data: StringProperty()
    json_import_data: CollectionProperty(type=JsonImportData)
    active_all: BoolProperty(default=True,update=toggle_active)
    index: IntProperty()
    mode: EnumProperty(items=(("UPDATE","Update Existing","Update","FILE_REFRESH",0),("ADD","Add as New","Add as New","FORWARD",1)))
    
    @classmethod
    def poll(cls, context):
        return True
    
    def check(self,context):
        return True
    
    def draw(self, context):
        layout = self.layout 
        
        row = layout.row()
        row.prop(self, "mode", expand=True)
        col = layout.column()
        box = col.box()
        box.prop(self, "active_all", text="Import All")
        col.template_list("COATOOLS_UL_JsonImport", "dummy", self, "json_import_data", self, "index", rows=10)

    def invoke(self, context, event):
        
        sprite_data = eval(self.json_data)
        for node in sprite_data["nodes"]:
            item = self.json_import_data.add()
            item.name = node["name"]
            item.active = True
        
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene
        sprite_data = eval(self.json_data)
        
        ext = os.path.splitext(self.filepath)[1]
        folder = (os.path.dirname(self.filepath))
        
        for object in bpy.context.selected_objects:
            object.select_set(False)
                
        sprite_object = functions.get_sprite_object(context.active_object)
            

        
        if "name" in sprite_data:
            sprite_object.name = sprite_data["name"]
            
        if "nodes" in sprite_data:
            for i,sprite in enumerate(sprite_data["nodes"]):
                if sprite["name"] in self.json_import_data and self.json_import_data[sprite["name"]].active:
                    
                    filepath = os.path.join(folder,sprite["resource_path"])
                    pos = [sprite["position"][0],-sprite["z"],sprite["position"][1]]
                    offset = [sprite["offset"][0],0,sprite["offset"][1]]
                    parent = sprite_object.name
                    scale = functions.get_addon_prefs(context).sprite_import_export_scale
                    
                    
                    if self.mode == "ADD":
                        bpy.ops.coa_tools.import_sprite(path=filepath,parent=sprite_object.name,scale=scale,pos=pos,tilesize=[1,1],offset=offset)
                    if self.mode == "UPDATE":
                        if sprite["name"] in context.scene.objects:
                            obj = context.scene.objects[sprite["name"]]
                            obj.select_set(True)
                            context.scene.view_layers[0].objects.active = obj
                            bpy.ops.coa_tools.reimport_sprite(filepath=filepath,name=sprite["name"],scale=scale,pos=pos,offset=offset)
                        else:
                            bpy.ops.coa_tools.import_sprite(path=filepath,parent=sprite_object.name,scale=scale,pos=pos,tilesize=[1,1],offset=offset)
                    
                    if sprite["name"] in bpy.data.objects:
                        obj = bpy.data.objects[sprite["name"]]
                        obj.parent = sprite_object
                
        context.scene.view_layers[0].objects.active = sprite_object    
        
        return {"FINISHED"}
        

# ############################################################################################## Import Single Sprite
class COATOOLS_OT_ImportSprite(bpy.types.Operator):
    bl_idname = "coa_tools.import_sprite"
    bl_label = "Import Sprite"
    bl_options = {"REGISTER", "UNDO"}
    
    path: StringProperty(name="Sprite Path", default="",subtype="FILE_PATH")
    pos: FloatVectorProperty(default=Vector((0, 0, 0)))
    scale: FloatProperty(name="Sprite Scale", default=.01)
    offset: FloatVectorProperty(default=Vector((0, 0, 0)))
    tilesize: FloatVectorProperty(default=Vector((1, 1)), size=2)
    parent: StringProperty(name="Parent Object", default="None")

    def create_verts(self, width, height, pos, me, tag_hide=False):
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(me)
        vert1 = bm.verts.new(Vector((0, 0, -height)) * self.scale)
        vert2 = bm.verts.new(Vector((width, 0, -height)) * self.scale)
        vert3 = bm.verts.new(Vector((width, 0, 0)) * self.scale)
        vert4 = bm.verts.new(Vector((0, 0, 0)) * self.scale)

        bm.faces.new([vert1, vert2, vert3, vert4])

        bmesh.update_edit_mesh(me)

        if tag_hide:
            for vert in bm.verts:
                vert.hide_viewport = True

            for edge in bm.edges:
                edge.hide_viewport = True    
        
        bmesh.update_edit_mesh(me)
        bpy.ops.object.mode_set(mode="OBJECT")
    
    def create_mesh(self, context, name="Sprite", width=100, height=100, pos=Vector((0, 0, 0))):
        me = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, me)
        # context.collection.objects.link(obj)
        functions.link_object(context, obj)
        context.scene.view_layers[0].objects.active = obj
        obj.select_set(True)

        self.create_verts(width, height, pos, me, tag_hide=False)
        v_group = obj.vertex_groups.new(name="coa_base_sprite")
        v_group.add([0, 1, 2, 3], 1.0, "REPLACE")
        v_group.lock_weight = True
        mod = obj.modifiers.new("coa_base_sprite", "MASK")
        mod.vertex_group = "coa_base_sprite"
        mod.invert_vertex_group = True
        mod.show_in_editmode = True
        mod.show_render = False
        mod.show_viewport = False
        mod.show_on_cage = True
        
        obj.data.uv_layers.new(name="UVMap")
        
        obj.location = Vector((pos[0],pos[1],-pos[2]))*self.scale + Vector((self.offset[0],self.offset[1],self.offset[2]))*self.scale
        obj.coa_tools["sprite"] = True
        if self.parent != "None":
            obj.parent = bpy.data.objects[self.parent]
        return obj

    def create_material(self, context, mesh, name="Sprite"):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        node_tree = mat.node_tree
        output_node = None
        # cleanup node tree
        for node in mat.node_tree.nodes:
            if node.type != "OUTPUT_MATERIAL":
                mat.node_tree.nodes.remove(node)
            else:
                output_node = node
        # create all required nodes and connect them
        tex_node = node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.interpolation = "Closest"
        tex_node.image = bpy.data.images[name]

        bpy.ops.coa_tools.create_material_group()
        coa_node_tree = bpy.data.node_groups[CONSTANTS.COA_NODE_GROUP_NAME]
        coa_node = node_tree.nodes.new("ShaderNodeGroup")
        coa_node.name = "COA Material"
        coa_node.label = "COA Material"
        coa_node.node_tree = coa_node_tree
        coa_node.inputs["Alpha"].default_value = 1.0
        coa_node.inputs["Modulate Color"].default_value = [1,1,1,1]
        
        node_tree.links.new(coa_node.inputs["Texture Color"], tex_node.outputs["Color"], verify_limits=True)
        node_tree.links.new(coa_node.inputs["Texture Alpha"], tex_node.outputs["Alpha"], verify_limits=True)
        node_tree.links.new(coa_node.outputs["BSDF"], output_node.inputs["Surface"], verify_limits=True)

        # position nodes in node tree
        tex_node.location = (0, 0)
        coa_node.location = (280, 0)
        output_node.location = (460, 0)
        mesh.materials.append(mat)
        return mat

    def execute(self, context):
        if os.path.exists(self.path):
            data = bpy.data
            sprite_name = os.path.basename(self.path)

            sprite_found = False
            for image in bpy.data.images:
                if os.path.exists(bpy.path.abspath(image.filepath)) and os.path.exists(self.path):
                    if os.path.samefile(bpy.path.abspath(image.filepath), self.path):
                        sprite_found = True
                        img = image
                        img.reload()
                        break
            if not sprite_found:
                img = data.images.load(self.path)

            obj = self.create_mesh(context, name=img.name, width=img.size[0], height=img.size[1], pos=self.pos)
            mat = self.create_material(context, obj.data, name=img.name)
            msg = sprite_name + " Sprite created."
            
            selected_objects = []
            for obj2 in context.selected_objects:
                selected_objects.append(obj2)
                if obj2 != context.active_object:
                    obj2.select_set(False)
            obj.coa_tools.z_value = int(-self.pos[1])
            for obj2 in selected_objects:
                obj2.select_set(True)
            
            self.report({'INFO'}, msg)
            return{'FINISHED'}
        else:
            self.report({'WARNING'}, 'File does not exist.')
            return{'CANCELLED'}
    
    def invoke(self, context, event):
        wm = context.window_manager 
        return wm.invoke_props_dialog(self)
        
# ############################################################################################## Import Multiple Sprites
class COATOOLS_OT_ImportSprites(bpy.types.Operator, ImportHelper):
    bl_idname = "coa_tools.import_sprites"
    bl_label = "Import Sprites"
    bl_description = "Imports sprites into Blender"
    
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    
    filepath: StringProperty(
        default="test"
         )
    
    filter_image: BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    filter_movie: BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    filter_folder: BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    filter_glob: StringProperty(default='*.json',options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    #use_setting = None
    replace: BoolProperty(name="Update Existing",default=True)
    
    def execute(self, context):
        sprite_object = functions.get_sprite_object(context.active_object)
        
        context.space_data.shading.type = "RENDERED"
        context.scene.view_settings.view_transform = "Standard"
        
        ext = os.path.splitext(self.filepath)[1]
        folder = (os.path.dirname(self.filepath))
        
        for object in context.selected_objects:
            object.select_set(False)

        if ext not in [".json"]:
            for i in self.files:
                filepath = (os.path.join(folder, i.name))
                if not self.replace or i.name not in bpy.data.objects:
                    bpy.ops.coa_tools.import_sprite(path=filepath,parent=sprite_object.name,scale=functions.get_addon_prefs(context).sprite_import_export_scale)
                else:
                    bpy.ops.coa_tools.reimport_sprite(filepath=filepath,name=i.name, reposition=False)
        else:
            data_file = open(self.filepath)
            sprite_data = json.load(data_file)
            data_file.close()
            
            bpy.ops.coa_tools.load_json_data("INVOKE_DEFAULT",json_data = str(sprite_data),filepath=self.filepath)

        bpy.ops.view3d.view_axis(type='FRONT', align_active=False, relative=False)
        # if bpy.context.screen.coa_view == "3D":
        #     bpy.ops.view3d.viewnumpad(type="FRONT")
        # if context.space_data.region_3d.is_perspective:
        #     bpy.ops.view3d.view_persportho()
        bpy.ops.ed.undo_push(message="Sprite Import")                   
        return{'FINISHED'}
    

    
class COATOOLS_OT_ReImportSprite(bpy.types.Operator, ImportHelper):
    bl_idname = "coa_tools.reimport_sprite"
    bl_label = "Reimport Sprite"
    bl_description="Reimports sprites"
    
    #files: CollectionProperty(type=bpy.types.PropertyGroup)
    
    filepath: StringProperty(
        default="test"
         )
    
    filter_image: BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    filter_folder: BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})

    name: StringProperty(default="")
    pos: FloatVectorProperty(default=Vector((0,0,0)))
    scale: FloatProperty(default=.01)
    offset: FloatVectorProperty(default=Vector((0,0,0)))
    reposition: BoolProperty(default=True)
    
    def move_verts(self,obj,ratio_x,ratio_y):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.reveal()
        bpy.ops.object.mode_set(mode="OBJECT")
        
        shapekeys = [obj.data.vertices]
        if obj.data.shape_keys != None:
            shapekeys = []
            for shapekey in obj.data.shape_keys.key_blocks:
                shapekeys.append(shapekey.data)
        
        for shapekey in shapekeys:
            for vert in shapekey:
                co_x = vert.co[0] * ratio_x
                co_y = vert.co[2] * ratio_y
                vert.co = Vector((co_x,0,co_y))
    
    def draw(self,context):
        obj = context.active_object
        if self.name in bpy.data.objects:
            obj = bpy.data.objects[self.name]
        
        layout = self.layout
        col = layout.column()
    
    def execute(self, context):
        obj = bpy.data.objects[self.name]
        sprite_found = False

        # get image
        img = None
        for image in bpy.data.images:
            if os.path.exists(bpy.path.abspath(image.filepath)) and os.path.exists(self.filepath):
                if os.path.samefile(bpy.path.abspath(image.filepath),self.filepath):
                    sprite_found = True
                    img = image
                    prev_img_size = img.size[:]
                    img.reload()
                    break
        if not sprite_found:
            img = bpy.data.images.load(self.filepath)

        
        scale = functions.get_addon_prefs(context).sprite_import_export_scale
        if self.name in bpy.data.objects:
            active_obj = bpy.data.objects[self.name]
            obj_hide = active_obj.hide_viewport
            active_obj.hide_viewport = False
            obj = context.active_object
            if self.name != "" and self.name in bpy.data.objects:
                obj = bpy.data.objects[self.name]
                bpy.context.scene.view_layers[0].objects.active = obj
            mat = obj.active_material
            if mat.node_tree != None:
                for node in mat.node_tree.nodes:
                    if node.label == "COA Material":
                        node.inputs["Texture Color"].links[0].from_node.image = img

            img_dimension = img.size
            
            obj_dimension = Vector(obj.dimensions)
            obj_dimension[0] /= obj.scale[0]
            obj_dimension[1] /= obj.scale[1]
            obj_dimension[2] /= obj.scale[2]
            
            pos = self.pos
            if self.reposition:
                obj.location = Vector((pos[0],pos[1],-pos[2]))*self.scale + Vector((self.offset[0],self.offset[1],self.offset[2]))*self.scale
            
            sprite_dimension = Vector(obj_dimension) * (1/scale)

            ratio_x = round(img_dimension[0] / prev_img_size[0], 4)
            ratio_y = round(img_dimension[1] / prev_img_size[1], 4)
            print(self.name, "ratio x:", ratio_x, " - ratio y:", ratio_y)
            self.move_verts(obj, ratio_x, ratio_y)

            bpy.context.scene.view_layers[0].objects.active = active_obj
            active_obj.hide_viewport = obj_hide
        return {'FINISHED'}
