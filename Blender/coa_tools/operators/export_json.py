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
import bpy_types
import json
import os
import shutil
from .. functions import *
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
from collections import OrderedDict
import math
import time

class ExportToJson(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object.export_to_json"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export To Json"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    # ExportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob = StringProperty(default="*.json",options={'HIDDEN'},)
    export_anims = BoolProperty(name="Export Animation Collections",description="Exports All Animation Collections",default=True,)
    export_only_deform_bones = BoolProperty(name="Export Only Deform Bones",description="Exports All Animation Collections",default=True,)
    
    export_dict = OrderedDict()
    sprite_object = None
    armature = None
    children = []
    bone_sprite_constraint = {}
    export_path = ""
    scale_multiplier = 100.0
    time_idx_hist = 0
    time_idx = 0
    
    ### gets the sprite offset from the upper left sprite corner to the pivot point of the bone.
    def get_bounds_and_center(obj):
        sprite_center = Vector((0,0,0))
        bounds = []
        for i,corner in enumerate(obj.bound_box):
            world_corner = obj.matrix_local * Vector(corner)
            sprite_center += world_corner
            if i in [0,1,4,5]:
                bounds.append(world_corner)
        sprite_center = sprite_center*0.125
        return[sprite_center,bounds]
    
    ### gets the local dimension of a mesh. 
    def get_local_dimension(self,obj):
        x0 = 10000000000*10000000000
        x1 = -10000000000*10000000000
        y0 = 10000000000*10000000000
        y1 = -100000000000*10000000000
        
        for vert in obj.data.vertices:
            if vert.co[0] < x0:
                x0 = vert.co[0]
            if vert.co[0] > x1:
                x1 = vert.co[0]
            if vert.co[2] < y0:
                y0 = vert.co[2]
            if vert.co[2] > y1:
                y1 = vert.co[2]
        return [x1-x0,y1-y0]
    
    def get_image_scale(self,obj):
        dimension = self.get_local_dimension(obj)
        img = obj.material_slots[0].material.texture_slots[0].texture.image
        scale_x = round((dimension[0])/img.size[0],5)*self.scale_multiplier
        scale_y = round((dimension[1])/img.size[1],5)*self.scale_multiplier
        return[scale_x,scale_y]
    
    def get_sprite_scale(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        scale_x = obj.scale[0]*self.get_image_scale(obj)[0]*obj.coa_tiles_x
        scale_y = obj.scale[2]*self.get_image_scale(obj)[1]*obj.coa_tiles_y
        
        return [scale_x,scale_y]
    
        
    def get_sprite_offset(self,obj_name):
        obj = bpy.data.objects[obj_name]
        x = 1000000000000000000
        y = -1000000000000000000
        for vert in obj.data.vertices:
            if vert.co[0] < x:
                x = vert.co[0]
            if vert.co[2] > y:
                y = vert.co[2]
        corner_vert = Vector((x,0,y)) 
        offset =  corner_vert * self.scale_multiplier
        offset[0] /= self.get_image_scale(obj)[0]
        offset[2] /= self.get_image_scale(obj)[1]
        offset_2d = [offset[0],-offset[2]]
        return offset_2d
    
    def get_sprite_tilesize(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        return [obj.coa_tiles_x,obj.coa_tiles_y]
    
    def get_sprite_frame_index(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        return int(obj.coa_sprite_frame)
    
    def get_modulate_color(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        return [obj.coa_modulate_color[0],obj.coa_modulate_color[1],obj.coa_modulate_color[2]]
    
    def get_sprite_opacity(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        return obj.coa_alpha
    
    
    def get_sprite_rotation(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        euler_rot = obj.matrix_basis.to_euler()
        degrees = math.degrees(euler_rot[1])
        return -math.radians(degrees)
        
    ### convert windows slashes to linux slashes    
    def change_path_slashes(self,path):
        path = path.replace("\\","/")
        return path
    
    ### returns a main deforming bone of a mesh. needed to assign specific bones to meshes
    def get_bone_sprites(self,sprite,armature):
        if len(sprite.vertex_groups) == 0 and sprite.parent_bone == '':
            return sprite.parent.name
        elif sprite.parent_bone != '':
            return sprite.parent_bone
        
        vertex_count = len(sprite.data.vertices)
        vertex_weights_average = {}
        for vertex_group in sprite.vertex_groups:
            if vertex_group.name in armature.data.bones:
                weight = 0
                for i in range(vertex_count):
                    try:
                        weight += vertex_group.weight(i)
                    except:
                        pass
                weight = weight/vertex_count
                vertex_weights_average[vertex_group.name] = weight
        bone = max(vertex_weights_average, key=vertex_weights_average.get)
        return bone
    
    def get_edit_bones(self,context):
        self.edit_bone_matrices = {}
        active_object = context.active_object
        context.scene.objects.active = self.armature
        mode = self.armature.mode
        bpy.ops.object.mode_set(mode="EDIT")
        
        for bone in self.armature.data.bones:
            edit_bone = self.armature.data.edit_bones[bone.name]
            self.edit_bone_matrices[bone.name] = edit_bone.matrix
            edit_bone.name = bone.name
        
        bpy.ops.object.mode_set(mode=mode)
        context.scene.objects.active = active_object
            
    def get_bone_transformation(self,bone):
        context = bpy.context
        pose_bone = self.armature.pose.bones[bone.name]
        
        edit_bone_matrix = self.edit_bone_matrices[bone.name]
        
        mat_local =  pose_bone.matrix
        scale = mat_local.decompose()[2]
        scale_mat = Matrix.Identity(4)
        scale_mat[0][0] = scale[0]
        scale_mat[1][1] = scale[1]
        scale_mat[2][2] = scale[2]
        mat_local = (mat_local*(edit_bone_matrix*scale_mat).inverted())*scale_mat
        return mat_local
        
        
    def get_bone_scale(self,bone):
        pose_bone = self.armature.pose.bones[bone.name]
        
        if bone.parent != None:
            local_mat = self.get_bone_transformation(bone.parent).inverted() * self.get_bone_transformation(bone)
        else:
            local_mat = self.get_bone_transformation(bone)    
        bone_scale = local_mat.decompose()[2]
        bone_scale_2d = [bone_scale[1],bone_scale[1]]    
        return bone_scale_2d
    
    def get_relative_bone_pos(self,bone,type):
        pose_bone = self.armature.pose.bones[bone.name]
        pose_bone_location = pose_bone.location
        
        if bone.parent == None:
            if type == "HEAD":
                bone_pos = (((bone.matrix_local.to_4x4() * pose_bone.matrix_basis).to_translation())) * self.scale_multiplier
                bone_pos_2d = [bone_pos[0],-bone_pos[2]]
            elif type == "TAIL":    
                bone_pos = (bone.tail_local - bone.head_local) * self.scale_multiplier
                bone_pos_2d = [bone_pos[0],bone_pos[2]]
            return bone_pos_2d
        else:
            if type == "HEAD":
                bone_pos = (((bone.matrix_local.to_4x4() * pose_bone.matrix_basis).to_translation()) - (bone.parent.matrix_local.to_4x4().to_translation())) * self.scale_multiplier
                bone_pos_2d = [bone_pos[0],-bone_pos[2]]
            elif type == "TAIL":
                bone_pos = (bone.tail_local - bone.head_local) * self.scale_multiplier
                bone_pos_2d = [bone_pos[0],bone_pos[2]]
            return bone_pos_2d
    
    def get_bone_rotation(self,bone):
        pose_bone = self.armature.pose.bones[bone.name]
        
        if bone.parent != None:
            local_mat = self.get_bone_transformation(bone.parent).inverted() * self.get_bone_transformation(bone)
        else:
            local_mat = self.get_bone_transformation(bone)    
        bone_euler_rot = local_mat.decompose()[1].to_euler()
        
        degrees = round(math.degrees(bone_euler_rot.y),2)
        return -math.radians(degrees)
    
    def get_relative_mesh_pos(self, parent, obj):
        if type(parent) == bpy_types.Bone:
            relative_pos = (obj.matrix_basis.to_translation() - parent.head_local) * self.scale_multiplier
        else:
            relative_pos = obj.matrix_local.to_translation() * self.scale_multiplier
            
        relative_pos_2d = [relative_pos[0],-relative_pos[2]]
        return relative_pos_2d
    
    ### get the sprite resource path and copy image resources in a subfolder of the json location
    def get_sprite_path(self,sprite_name):
        obj = bpy.data.objects[sprite_name]
        mat = obj.material_slots[0].material
        tex = mat.texture_slots[0].texture
        img = tex.image
        
        img_path = self.change_path_slashes(img.filepath)
        if "//" in img_path:
            img_path = img_path.replace("//","")
            img_path = os.path.join(bpy.path.abspath("//"),img_path)
        img_path = self.change_path_slashes(img_path)
        ### create resource directory
        res_dir_path = os.path.join(os.path.dirname(self.export_path),"sprites")
        copied_res_path = os.path.join(res_dir_path,os.path.basename(img_path))
        
        if not os.path.exists(res_dir_path):
            os.makedirs(res_dir_path)
        if os.path.isfile(img_path):# and not os.path.isfile(copied_res_path):
            shutil.copy(img_path,res_dir_path)
        else:
            original_path = img.filepath
            export_path = os.path.join(res_dir_path,sprite_name)
            img.filepath = export_path
            img.filepath_raw = export_path
            img.save()
            img.filepath = original_path
            img.filepath_raw = original_path
        
        rel_path = os.path.relpath(copied_res_path,os.path.dirname(self.export_path))
        return self.change_path_slashes(rel_path)

    def get_node_path(self,node,path_list):
        if type(node) == bpy_types.Bone:
            path_list.append(node.name)
            for child_node in node.parent_recursive:
                path_list.append(child_node.name)
        else:
            ### node is weigted to a bone
            if node.parent != None and node.parent.type != "ARMATURE":
                path_list.append(node.name)
                self.get_node_path(node.parent,path_list)
            elif node.parent != None and node.parent.type == "ARMATURE":
                path_list.append(node.name)
                self.get_node_path(self.armature.data.bones[self.get_bone_sprites(node,self.armature)],path_list)

        path = ""
        for i,item in enumerate(reversed(path_list)):   
            path += item
            if i < len(path_list)-1:
                 path += "/"
        return path     
            
    def get_z_value(self,sprite):
        obj = bpy.data.objects[sprite]
        return obj.coa_z_value
    
    
    def sprite_to_dict(self,sprite,bone=None):
        dict_sprites = OrderedDict()
        dict_sprites["name"] = sprite
        dict_sprites["type"] = "SPRITE"
        dict_sprites["node_path"] = str(self.get_node_path(bpy.data.objects[sprite],[]))#,suffix=sprite))
        dict_sprites["resource_path"] = self.get_sprite_path(sprite)
        dict_sprites["pivot_offset"] = self.get_sprite_offset(sprite)
        dict_sprites["position"] = self.get_relative_mesh_pos(bone,bpy.data.objects[sprite])
        dict_sprites["rotation"] = self.get_sprite_rotation(sprite)
        dict_sprites["scale"] = self.get_sprite_scale(sprite)
        dict_sprites["opacity"] = self.get_sprite_opacity(sprite)
        dict_sprites["z"] = self.get_z_value(sprite)
        dict_sprites["tiles_x"] = self.get_sprite_tilesize(sprite)[0]
        dict_sprites["tiles_y"] = self.get_sprite_tilesize(sprite)[1]
        dict_sprites["frame_index"] = self.get_sprite_frame_index(sprite)
        dict_sprites["children"] = []
        
        for child in bpy.data.objects[sprite].children:
            if child.type == "MESH":
                dict_sprites["children"].append(self.sprite_to_dict(child.name,bpy.data.objects[sprite]))
                
        return dict_sprites
    
    def bone_to_dict(self,bone):
        dict_bone = OrderedDict()
        dict_bone["name"] = bone.name
        dict_bone["type"] = "BONE"
        dict_bone["node_path"] = str(self.get_node_path(bone,[]))#,suffix=""))
        dict_bone["draw_bone"] = self.armature.data.bones[bone.name].coa_draw_bone
        dict_bone["bone_connected"] = bone.use_connect
        dict_bone["position"] = self.get_relative_bone_pos(bone,"HEAD")
        dict_bone["position_tip"] = self.get_relative_bone_pos(bone,"TAIL")
        dict_bone["rotation"] = self.get_bone_rotation(bone)
        dict_bone["scale"] = self.get_bone_scale(bone)
        dict_bone["z"] = self.armature.data.bones[bone.name].coa_z_value 
        dict_bone["children"] = []
        return dict_bone
    
    def armature_to_dict(self,bone):
        dict_bone = self.bone_to_dict(bone)
        
        sprites = []
        if bone.name in self.bone_sprite_constraint:
            sprites = self.bone_sprite_constraint[bone.name]  
        for sprite in sprites:        
            dict_bone["children"].append(self.sprite_to_dict(sprite,bone))
        
        for child in bone.children:
            sprites = []
            if child.name in self.bone_sprite_constraint:
                sprites = self.bone_sprite_constraint[child.name]
            if self.export_only_deform_bones:    
                if child.use_deform or len(child.children) > 0:
                    dict_bone["children"].append(self.armature_to_dict(child))
            else:
                dict_bone["children"].append(self.armature_to_dict(child))        
    
        return dict_bone    

    def get_collection_action(self,context,anim_collection):
        actions = []
        
        set_action(context,item=anim_collection)
        context.scene.update()     
        
        for action in bpy.data.actions:
            if anim_collection.name in action.name:
                actions.append(action)
        return actions
    
    def has_animation_data(self,animation_data,channel,bone=""):
        if animation_data == None:
            return False
        action = animation_data.action
        
        fcurve_data_found = False
        if action != None:
            for fcurve in action.fcurves:
                if channel in fcurve.data_path and bone in fcurve.data_path:
                    fcurve_data_found = True        
        return fcurve_data_found
    
    def has_keyframe(self,animation_data,name,property="any",frame=0):
        action = None
        if animation_data != None:
            action = animation_data.action
        else:
            return False
        keyframe_found = False 
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                if keyframe.co[0] == frame and name in fcurve.data_path and (property in fcurve.data_path or property=="any"):
                    keyframe_found = True
        return keyframe_found  
    
    def keyframe_to_dict(self,track,property,value,channels,key):
        time_idx_hist = channels[key][1]["time_idx_hist"]
        if os.path.basename(track) == property:
            if time_idx_hist in channels[key][0]:
                if channels[key][0][time_idx_hist]["value"] != value:
                    dict_value_entry = OrderedDict()
                    dict_value_entry["value"] = value
                    channels[key][0][self.time_idx] = dict_value_entry
                    
                    if time_idx_hist != self.time_idx_last:
                        channels[key][0][self.time_idx_last] = channels[key][0][time_idx_hist]
                    
                    channels[key][1]["time_idx_hist"] = self.time_idx
            elif self.f == 0 or (self.f and self.restpose):
                dict_value_entry = OrderedDict()
                dict_value_entry["value"] = value
                channels[key][0][self.time_idx] = dict_value_entry
                channels[key][1]["time_idx_hist"] = self.time_idx
    
    def has_constraint(self,bone,const_type):
        for constraint in bone.constraints:
            if constraint.type == const_type:
                return constraint.subtarget
        return None
    
    def const_bone_has_anim_data(self,bone_name,channel):
        p_bone = self.armature.pose.bones[bone_name]
        if self.has_constraint(p_bone,"STRETCH_TO"):
            return self.has_animation_data(self.armature.animation_data,channel,bone_name)
        else:
            return False
    
    def get_action_data(self,start,end,restpose=False):
        scene = bpy.context.scene
        self.restpose = restpose
        channels = OrderedDict()
        if self.armature != None:
            for bone in self.armature.data.bones:
                pose_bone = self.armature.pose.bones[bone.name]
                if bone.coa_data_path == "":
                    bone.coa_data_path = "."
                if (self.has_animation_data(self.armature.animation_data,"location",bone.name) or self.const_bone_has_anim_data(bone.name,"location") or restpose or pose_bone.is_in_ik_chain or len(pose_bone.constraints) > 0) and bone.use_deform:
                    channels[self.get_node_path(bone,[])+":transform/pos"] = [OrderedDict(),{"node_name":bone.name,"time_idx_hist":"0.0","animation_data":self.armature.animation_data}]
                if (self.has_animation_data(self.armature.animation_data,"rotation",bone.name) or self.const_bone_has_anim_data(bone.name,"rotation") or restpose or pose_bone.is_in_ik_chain or len(pose_bone.constraints) > 0) and bone.use_deform:
                    channels[self.get_node_path(bone,[])+":transform/rot"] = [OrderedDict(),{"node_name":bone.name,"time_idx_hist":"0.0","animation_data":self.armature.animation_data}]
                if (self.has_animation_data(self.armature.animation_data,"scale",bone.name) or self.const_bone_has_anim_data(bone.name,"scale") or restpose or pose_bone.is_in_ik_chain or len(pose_bone.constraints) > 0) and bone.use_deform:
                    channels[self.get_node_path(bone,[])+":transform/scale"] = [OrderedDict(),{"node_name":bone.name,"time_idx_hist":"0.0","animation_data":self.armature.animation_data}]
            
        for child in self.children:
            if child.type == "MESH":
                if child.coa_data_path == "":
                    child.coa_data_path = "."
                if self.has_animation_data(child.animation_data,"location") or restpose:
                    channels[self.get_node_path(child,[])+":transform/pos"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                if self.has_animation_data(child.animation_data,"rotation") or restpose:
                    channels[self.get_node_path(child,[])+":transform/rot"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                if self.has_animation_data(child.animation_data,"scale") or restpose:
                    channels[self.get_node_path(child,[])+":transform/scale"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                if self.has_animation_data(child.animation_data,"coa_alpha") or restpose:
                    channels[self.get_node_path(child,[])+":visibility/opacity"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                if self.has_animation_data(child.animation_data,"coa_z_value") or restpose:
                    channels[self.get_node_path(child,[])+":z/z"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                if self.has_animation_data(child.animation_data,"coa_sprite_frame") or restpose:
                    channels[self.get_node_path(child,[])+":frame"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                if self.has_animation_data(child.animation_data,"coa_modulate_color") or restpose:
                    channels[self.get_node_path(child,[])+":modulate"] = [OrderedDict(),{"node_name":child.name,"time_idx_hist":"0.0","animation_data":child.animation_data}]
                    
        current_frame = scene.frame_current
        if restpose:
            start=0
            end=1
        self.start = start
        self.end = end
        interval = 1
         
        for f in range(start,end+1):
            self.f = f  

            for key in channels:
                obj_name = os.path.basename(key.split(":")[0])
                track = os.path.basename(key.split(":")[1])
                
                p_bone = None
                
                node_type = "SPRITE"
                if self.armature != None and obj_name in self.armature.data.bones:
                    node_type = "BONE"
                    p_bone = self.armature.pose.bones[obj_name]
                elif obj_name in bpy.data.objects:
                    node_type = "SPRITE"
                
                
                if (f == start or f == end or f%interval == 0):# or (p_bone != None and (p_bone.is_in_ik_chain or self.has_constraint(p_bone,"COPY_ROTATION") or self.has_constraint(p_bone,"COPY_LOCATION"))):
                    scene.frame_set(f)
                    self.time_idx = str((f)/scene.render.fps)
                    self.time_idx_last = str((f-interval)/scene.render.fps)
                    ### write bone keyframe data
                    if self.armature != None and obj_name in self.armature.data.bones:
                        bone = self.armature.data.bones[obj_name]
                        
                        ### bone transformations
                
                        self.keyframe_to_dict(track,"pos",self.get_relative_bone_pos(bone,"HEAD"),channels,key)
                        self.keyframe_to_dict(track,"rot",self.get_bone_rotation(bone),channels,key)
                        self.keyframe_to_dict(track,"scale",self.get_bone_scale(bone),channels,key)
                            
                    ### write sprite keyframe data        
                    if obj_name in bpy.data.objects:
                        sprite = obj_name
                        if len(key.split("/"+sprite)) > 1:
                            name = os.path.basename(key.split("/"+sprite)[0])
                            if name in self.armature.data.bones:
                                parent = self.armature.data.bones[name]
                            elif name in bpy.data.objects:
                                parent = bpy.data.objects[name]
                        else:
                            parent = self.sprite_object
                        
                        ### sprite transformations and other properties
                        self.keyframe_to_dict(track,"pos",self.get_relative_mesh_pos(parent,bpy.data.objects[sprite]),channels,key)
                        self.keyframe_to_dict(track,"rot",self.get_sprite_rotation(sprite),channels,key)
                        self.keyframe_to_dict(track,"scale",self.get_sprite_scale(sprite),channels,key)
                        self.keyframe_to_dict(track,"opacity",self.get_sprite_opacity(sprite),channels,key)
                        self.keyframe_to_dict(track,"z",self.get_z_value(sprite),channels,key)
                        self.keyframe_to_dict(track,"frame",self.get_sprite_frame_index(sprite),channels,key)
                        self.keyframe_to_dict(track,"modulate",self.get_modulate_color(sprite),channels,key)

                                     
        scene.frame_current = current_frame
        
        export_channels = OrderedDict()
        for key in channels:
            export_channels[key] = channels[key][0]
        
        return export_channels
                    
                    
    def execute(self, context):
        
        
        
        self.scale_multiplier = round(1/get_addon_prefs(context).sprite_import_export_scale,4)
        
        self.export_path = self.filepath
        #bpy.ops.ed.undo_push(message="Export Json")
        
        self.bone_sprite_constraint = {}
        self.export_dict = OrderedDict()
        
        self.sprite_object = get_sprite_object(context.active_object)
        self.armature = get_armature(self.sprite_object)
        self.children = get_children(context,self.sprite_object,[])
        
        if self.armature != None:
            self.get_edit_bones(context)
        #return{'FINISHED'}
        ### store frame and animation state
        if len(self.sprite_object.coa_anim_collections) > 0:
            current_anim_collection = self.sprite_object.coa_anim_collections[self.sprite_object.coa_tools.anim_collections_index]
            current_time_frame = context.scene.frame_current
            current_active_object = context.active_object
            current_selected_objects = []
            for obj in context.scene.objects:
                if obj.select:
                    current_selected_objects.append(obj)
        
        
        ### start export from here
        
        self.export_dict["name"] = self.sprite_object.name
        self.export_dict["changelog"] = [(time.strftime("%d/%m/%Y")+" - "+ time.strftime("%H:%M:%S"))]
        self.export_dict["nodes"] = []
        
        
        ### export armature with bones and attached sprites
        if self.armature != None:
            for child in self.children:   
            #for child in self.armature.children:
                if child in self.armature.children:
                    if child.type == "MESH":
                        bone = self.get_bone_sprites(child,self.armature)
                        if bone not in self.bone_sprite_constraint:
                            self.bone_sprite_constraint[bone] = []
                        if child.name not in self.bone_sprite_constraint[bone]:
                            self.bone_sprite_constraint[bone].append(child.name)
                
            for bone in self.armature.data.bones:
                if bone.name not in self.bone_sprite_constraint:
                    self.bone_sprite_constraint[bone.name] = []
            
            for bone in self.armature.data.bones:
                if bone.parent == None:
                    if bone.name in self.bone_sprite_constraint:
                        self.export_dict["nodes"].append(self.armature_to_dict(bone))     
        
        ### export sprites that are not attached to any armature
        for child in self.sprite_object.children:
            if child.type == "MESH":
                self.export_dict["nodes"].append(self.sprite_to_dict(child.name,self.sprite_object))
        
        ### animation export
        if self.export_anims:
            self.export_dict["animations"] = []
            if len(self.sprite_object.coa_anim_collections) > 0:
                for anim_collection in self.sprite_object.coa_anim_collections:
                    if anim_collection.name != "NO ACTION":
                        self.report({'INFO'},str("Exporting "+anim_collection.name)+" Animation")
                        
                        set_action(context,item=self.sprite_object.coa_anim_collections[1])
                        set_action(context,item=anim_collection)
                        
                        animation = OrderedDict()
                        animation["name"] = anim_collection.name
                        animation["fps"] = context.scene.render.fps
                        animation["start"] = (anim_collection.frame_start-1)/context.scene.render.fps
                        animation["length"] = (anim_collection.frame_end)/context.scene.render.fps
                        animation["keyframes"] = OrderedDict()
                        
                        baked_actions = self.get_collection_action(context,anim_collection)
                        all_channels = OrderedDict()
                        
                        if anim_collection.name == "Restpose" and self.armature != None:
                            self.armature.data.pose_position = "REST"
                            channels = self.get_action_data(anim_collection.frame_start,anim_collection.frame_end,restpose=True)
                            self.armature.data.pose_position = "POSE"
                        else:
                            channels = self.get_action_data(anim_collection.frame_start,anim_collection.frame_end)
                        #channels = self.get_action_data(anim_collection.frame_start,anim_collection.frame_end)
                        for key in channels:
                            all_channels[key] = channels[key]
                        animation["keyframes"] = channels
                        self.export_dict["animations"].append(animation)
                        
            if len(self.sprite_object.coa_anim_collections) > 1:
                set_action(context)
        ### generate json file with a pretty print settings
        json_file = json.dumps(self.export_dict, indent="\t", sort_keys=False)
        #print(json_file)
        
        text_file = open(self.export_path, "w")
        text_file.write(json_file)
        text_file.close()
        
        
        ### restore frame and animation state
        if len(self.sprite_object.coa_anim_collections) > 0:
            set_action(context,item=current_anim_collection)
            context.scene.frame_current = current_time_frame
            context.scene.objects.active = current_active_object
            for obj in current_selected_objects:
                obj.select = True
        
        self.report({'INFO'},"Json Export done.")
        bpy.ops.ed.undo_push(message="Export Json")
        return {"FINISHED"}
        