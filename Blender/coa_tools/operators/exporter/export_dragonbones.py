
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
import bmesh
import json
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
from collections import OrderedDict
from ... functions import *
import math
from mathutils import Vector,Matrix, Quaternion, Euler
import shutil
from . texture_atlas_generator import TextureAtlasGenerator
from ... import constants

json_data = OrderedDict({
            "info":"Generated with COA Tools",
            "frameRate": 24,
            "name": "Project Name",
            "version": "5.5",
            "compatibleVersion": "5.5",
            "armature": []
            })

armature_data = OrderedDict({
            "type":"Armature",
            "frameRate":24,
            "name":"Armature",
            "aabb":{"width":0,"y":0,"height":0,"x":0},
            "bone":[],
            "slot":[],
            "skin":[{"name":"","slot":[]}],
            "ik":[],
            "animation":[],
            "defaultActions":[{"gotoAndPlay":""}]
           })

animation_data = OrderedDict({
            "duration": 0,
            "playTimes": 0,
            "name": "Anim Name",
            "bone": [],
            "frame": [],
            "slot": [],
            "ffd": [],
            })

skin = OrderedDict({
        "name":"",
        "slot":[],
        })

atlas_data = {}

display = [
            OrderedDict({
                "edges": [],
                "uvs": [],
                "type": "mesh",
                "vertices": [],
                "transform": {
                    "x": -2
                },
                "userEdges": [],
                "width": 480,
                "triangles": [],
                "height": 480,
                "name": "output_file",
                "path": ""
            })
        ]


bone_default_pos = {}
bone_default_rot = {}
bone_uses_constraints = {}
vert_coords_default = {}
tex_pathes = {}
img_names = {} ### exported image names
tmp_slots_data = {}

def setup_armature_data(root_bone, armature_name):
    armature_data = OrderedDict({
                "type": "Armature",
                "frameRate": 24,
                "name": armature_name,
                "aabb": {"width":0,"y":0,"height":0,"x":0},
                "bone": [{"name":root_bone.name}],
                "slot": [],
                "skin": [{"name":"","slot":[]}],
                "ik": [],
                "animation": [],
                "defaultActions": [{"gotoAndPlay":""}]
               })
    return armature_data

def setup_json_project(project_name):
    json_data = OrderedDict({
                "info":"Generated with COA Tools",
                "frameRate": 24,
                "name": project_name,
                "version": "5.5",
                "compatibleVersion": "5.5",
                "armature": []
                })
    return json_data

def get_sprite_image_data(sprite_data):
    #mat = sprite.active_material
    mat = sprite_data.materials[0]
    for node in mat.node_tree.nodes:
        if node.type == "GROUP" and node.node_tree.name == constants.COA_NODE_GROUP_NAME:
            links = node.inputs[0].links
            tex_node = links[0].from_node
            img = tex_node.image if len(links) > 0 and tex_node.type == "TEX_IMAGE" else None

    return mat, img

def copy_textures(self,sprites,texture_dir_path):
    global img_names
    img_names = {}
    for sprite in sprites:
        if sprite.type == "MESH":
            imgs = []
            if sprite.coa_tools.type == "MESH":
                if len(sprite.data.materials) > 0:
                    mat, img = get_sprite_image_data(sprite.data)
                    if img != None:
                        imgs.append({"img":img,"key":sprite.data.name})
            elif sprite.coa_tools.type == "SLOT":
                for slot in sprite.coa_tools.slot:
                    if len(slot.mesh.materials) > 0:
                        mat, img = get_sprite_image_data(slot.mesh)
                        if img != None:
                            imgs.append({"img":img,"key":slot.mesh.name})

            for data in imgs:
                img = data["img"]
                key = data["key"]

                src_path = bpy.path.abspath(img.filepath)
                img_name = os.path.basename(src_path)
                dst_path = os.path.join(texture_dir_path,img_name)

                img_names[key] = img_name[:img_name.rfind(".")]

                if self.scene.coa_tools.export_image_mode == "IMAGES":
                    if os.path.isfile(src_path):
                        shutil.copyfile(src_path,dst_path)
                    else:
                        img.save_render(dst_path)



def remove_base_sprite(obj):
    bpy.context.view_layer.objects.active = obj
    obj.hide_set(False)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    verts = []

    if "coa_base_sprite" in obj.vertex_groups and obj.data.coa_tools.hide_base_sprite:
        v_group_idx = obj.vertex_groups["coa_base_sprite"].index
        for i,vert in enumerate(obj.data.vertices):
            for g in vert.groups:
                if g.group == v_group_idx:
                    verts.append(bm.verts[i])
                    break

    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')


    bmesh.ops.delete(bm,geom=verts,context='VERTS')
    bm = bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode="OBJECT")



##### get mesh data like vertices, edges, triangles and uvs   ##### Start

def get_mixed_vertex_data(obj):
    shapes = obj.data.shape_keys
    verts = []
    index = int(obj.active_shape_key_index)
    shape_key = obj.shape_key_add(name="tmp_mixed_mesh",from_mix=True)
    for vert in shape_key.data:
        coord = obj.matrix_world @ vert.co
        verts.append([vert.co[0],vert.co[1],vert.co[2]])
    obj.shape_key_remove(shape_key)
    obj.active_shape_key_index = index
    return verts

### get vertices information
def convert_vertex_data_to_pixel_space(verts):
    data = []
    for vert in verts:
        for i,coord in enumerate(vert):
            if i in [0,2]:
                multiplier = 1
                if i == 2:
                    multiplier = -1
                value = round(multiplier*coord*100,2)
                data.append(value)
    return data

### get edge information
def get_edge_data(bm,only_outer_edges=True):
    edges = []
    for edge in bm.edges:
            if (edge.is_boundary and only_outer_edges) or (not edge.is_boundary and not only_outer_edges):
                for i,vert in enumerate(edge.verts):
                    edges.append(vert.index)
    return edges

### get triangle information
def get_triangle_data(bm):
    triangles = []
    for face in bm.faces:
        for i,vert in enumerate(face.verts):
            triangles.append(vert.index)
    return triangles

### get mesh vertex corrseponding uv vertex
def uv_from_vert_first(uv_layer, v):
    for l in v.link_loops:
        uv_data = l[uv_layer]
        return uv_data.uv
    return None

### get uv information
def get_uv_data(bm):
    uvs = []
    uv_layer = bm.loops.layers.uv.active

    ### first get the total dimensions of the uv
    left = 0
    top = 0
    bottom = 1
    right = 1
    for vert in bm.verts:
        uv_first = uv_from_vert_first(uv_layer, vert)
        for i, val in enumerate(uv_first):
            if i == 0:
                left = max(left, val)
                right = min(right, val)
            else:
                top = max(top, val)
                bottom = min(bottom, val)
    height = top - bottom
    width = left - right
    ### get uv coordinates and map them from 0 to 1 to total dimension that have been calculated before
    for vert in bm.verts:
        uv_first = uv_from_vert_first(uv_layer, vert)
        for i,val in enumerate(uv_first):
            if i == 1:
                value = -val + height
                final_value = round((value + bottom) / height, 3)
                uvs.append(final_value)
            else:
                value = val
                final_value = round((value - right)/width, 3)
                uvs.append(final_value)
    return uvs

def convert_color_channel(c):
    if c < 0.0031308:
        srgb = 0.0 if c < 0.0 else c * 12.92
    else:
        srgb = 1.055 * math.pow(c, 1.0 / 2.4) - 0.055

    return srgb

def get_modulate_color(sprite):
    color = sprite.coa_tools.modulate_color
    r = convert_color_channel(color.r)
    g = convert_color_channel(color.g)
    b = convert_color_channel(color.b)

    alpha = sprite.coa_tools.alpha
    color_data = {"rM":int(100*r),"gM":int(100*g),"bM":int(100*b),"aM":int(100*alpha)}
    return color_data

##### get mesh data like vertices, edges, triangles and uvs   ##### End

def get_bone_with_most_influence(self, sprite):
    vertex_groups = sprite.vertex_groups
    max_weight = 0
    bone = None
    for v_group in vertex_groups:
        if v_group.name in self.armature.data.bones:
            total_weight = 0
            for i,vert in enumerate(sprite.data.vertices):
                try:
                    total_weight += v_group.weight(vert.index)
                except:
                    pass
            if total_weight > max_weight:
                max_weight = float(total_weight)
                bone = self.armature.data.bones[v_group.name]
    return bone

### get slot data
def get_slot_data(self,sprites):
    slot_data = []
    for sprite in sprites:
        if sprite.type == "MESH":
            slot = OrderedDict()
            slot["name"] = sprite.name
            if len(sprite.data.vertices) != 4:
                slot["parent"] = self.sprite_object.name #sprite.parent.name
            else:
                bone_parent = get_bone_with_most_influence(self, sprite)
                if bone_parent != None:
                    slot["parent"] = bone_parent.name
                else:
                    slot["parent"] = self.sprite_object.name

            slot_data.append(slot)

            if len(sprite.coa_tools.slot) > 0:
                slot["displayIndex"] = sprite.coa_tools.slot_index

            color = get_modulate_color(sprite)
            if color["rM"] != 100 or color["gM"] != 100 or color["bM"] != 100 or color["aM"] != 100:
                slot["color"] = color
    return slot_data

def normalize_weights(obj, armature, threshold):
    for vert in obj.data.vertices:
        weight_total = 0.0
        groups = []
        for group in vert.groups:
            vgroup = obj.vertex_groups[group.group]
            group_name = vgroup.name
            if (group.weight > threshold and armature == None) or (group.weight > threshold and armature != None and group_name in armature.data.bones):
                groups.append(group)

        for group in groups:
            vgroup = obj.vertex_groups[group.group]
            weight_total += group.weight
        for group in groups:
            group.weight = 1*(group.weight/weight_total)

### get bone data
def create_cleaned_armature_copy(self,armature,sprites):
    context = bpy.context
    if armature != None:
        scene = bpy.context.scene

        armature_data = armature.data.copy()
        armature_copy = armature.copy()
        armature_copy.data = armature_data
        armature_copy.name = "COA_EXPORT_ARMATURE"

        context.collection.objects.link(armature_copy)

        delete_non_deform_bones(self,armature_copy,sprites)
        create_copy_transform_constraints(self,armature,armature_copy)

        ### store armature rest position. Relevant for later animation calculations
        scale = 1/get_addon_prefs(context).sprite_import_export_scale

        armature_copy.data.pose_position = "REST"
        armature.data.pose_position = "REST"
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        for bone in armature_copy.data.bones:
            transformations = {}
            transformations["bone_pos"] = get_bone_pos(armature_copy,bone,scale)
            transformations["bone_rot"] = get_bone_angle(armature_copy,bone) if not bone_uses_constraints[bone.name] else get_bone_angle(armature_copy,bone,relative=False)
            transformations["bone_scale"] = get_bone_scale(armature_copy,bone) if not bone_uses_constraints[bone.name] else get_bone_scale(armature_copy,bone,relative=False)


            self.armature_restpose[bone.name] = transformations
        armature_copy.data.pose_position = "POSE"
        armature.data.pose_position = "POSE"
        return armature_copy
    return None


### is used for export armature. All non deform bones will be deleted and deform bone animations baked in later process
def delete_non_deform_bones(self,armature,sprites):
    global bone_uses_constraints
    bone_uses_constraints = {}
    context = bpy.context
    context.view_layer.objects.active = armature

    bpy.ops.object.mode_set(mode="EDIT")

    for bone in armature.data.bones:
        pbone = armature.pose.bones[bone.name]
        ebone = armature.data.edit_bones[bone.name]
        bone_uses_constraints[pbone.name] = check_if_bone_uses_constraints(pbone)
        # if pbone.is_in_ik_chain or len(pbone.constraints) > 0:
        #     ebone.parent = None

        is_deform_bone = bone_is_deform_bone(self,bone,sprites)
        is_driver = bone_is_driver(bone,sprites)
        is_const_target = bone_is_constraint_target(bone,armature)
        has_children = len(bone.children) > 0

        if (not is_deform_bone and is_driver) or (not is_deform_bone and is_const_target) or (not is_deform_bone and not has_children) or (not is_deform_bone and not bone.use_deform):
            armature.data.edit_bones.remove(armature.data.edit_bones[bone.name])

    bpy.ops.object.mode_set(mode="OBJECT")

def create_copy_transform_constraints(self, armature_from, armature_to):
    for bone in armature_to.pose.bones:
        for const in bone.constraints:
            bone.constraints.remove(const)
        if bone.name in armature_from.pose.bones:
            const = bone.constraints.new("COPY_TRANSFORMS")
            const.target = armature_from
            const.subtarget = bone.name
            const.target_space = "POSE"
            const.owner_space = "POSE"

def bone_is_deform_bone(self,bone,sprites):
    for sprite in sprites:
        if sprite.type == "MESH":
            init_mesh = sprite.data
            meshes = []
            ### get a list of all meshes in sprite -> slot objects containt multiple meshes
            if sprite.coa_tools.type == "MESH":
                meshes.append(sprite.data)
            elif sprite.coa_tools.type == "SLOT":
                for slot in sprite.coa_tools.slot:
                    meshes.append(slot.mesh)

            ### check all meshes if bone is deforming that mesh
            for mesh in meshes:
                sprite.data = mesh
                if sprite.parent_bone == bone.name:
                    sprite.data = init_mesh
                    return True
                if not bone.name in sprite.vertex_groups:
                    break
                else:
                    v_group = sprite.vertex_groups[bone.name]
                    for vert in sprite.data.vertices:
                        try:
                            weight = v_group.weight(vert.index)
                            if weight > 0:
                                sprite.data = init_mesh
                                return True
                        except:
                            pass
            sprite.data = init_mesh
    return False

def check_if_bone_uses_constraints(pbone):
    return pbone.is_in_ik_chain or len(pbone.constraints) > 0

def bone_is_driver(bone,sprites):
    for sprite in sprites:
        if sprite.type == "MESH":
            meshes = []
            if sprite.coa_tools.type == "MESH":
                meshes.append(sprite.data)
            elif sprite.coa_tools.type == "SLOT":
                for slot in sprite.coa_tools.slot:
                    meshes.append(slot.mesh)

            all_bone_targets = []
            if sprite.animation_data != None:
                for driver in sprite.animation_data.drivers:
                    bone_targets = get_driver_bone_target(driver)
                    all_bone_targets += bone_targets
            for mesh in meshes:
                if mesh.animation_data != None:
                    for driver in mesh.animation_data.drivers:
                        bone_targets = get_driver_bone_target(driver)
                        all_bone_targets += bone_targets
                if mesh.shape_keys != None and mesh.shape_keys.animation_data != None:
                    for driver in mesh.shape_keys.animation_data.drivers:
                        bone_targets = get_driver_bone_target(driver)
                        all_bone_targets += bone_targets
                if bone.name in all_bone_targets:
                    return True
    return False

def bone_is_constraint_target(bone,armature):
    for pbone in armature.pose.bones:
        for const in pbone.constraints:
            if hasattr(const,"subtarget") and const.subtarget == bone.name:
                return True
    return False


### get skin data
def get_skin_slot(self,sprite,armature,scale,slot_data=None):
    context = bpy.context
    sprite_name = str(sprite.name)
    sprite_data_name = sprite.data.name if slot_data == None else slot_data.name
    ### make a sprite duplicate and make it active
    if slot_data == None:
        sprite_data = sprite.data.copy()
    else:
        sprite_data = slot_data.copy()
    sprite = sprite.copy()
    sprite.data = sprite_data
    context.collection.objects.link(sprite)
    context.view_layer.objects.active = sprite

    ### normalize weights
    normalize_weights(sprite, armature, 0.0)
    for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    with bpy.context.temp_override(object=sprite, edit_object=sprite):
                        bpy.ops.object.vertex_group_clean(group_select_mode='ALL', keep_single=True)
    ###

    global tmp_sprites
    tmp_slots_data[sprite_data_name] = {"data":sprite_data,"object":sprite,"name":sprite_data_name}

    ### get sprite material, texture and img data
    mat, img = get_sprite_image_data(sprite_data)
    if sprite_data_name in img_names:
        tex_path = os.path.join(self.scene.coa_tools.project_name+"_texture", img_names[sprite_data_name])
        tex_pathes[sprite_name] = tex_path
    ### delete basesprite mesh in sprite duplicate
    remove_base_sprite(sprite)

    ### get display data of a sprite
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(sprite.data)

    ### generate display data dictionary
    display_data = OrderedDict()

    ### get general skin information
    display_data["name"] = sprite_data_name#sprite_name
    if len(sprite.data.vertices) != 4:
        display_data["type"] = "mesh"
        if self.scene.coa_tools.export_image_mode == "IMAGES":
            display_data["path"] = img_names[sprite_data_name]

        if self.scene.coa_tools.export_image_mode == "IMAGES":
            display_data["width"] = int(img.size[0])
            display_data["height"] = int(img.size[1])
        elif self.scene.coa_tools.export_image_mode == "ATLAS":
            display_data["width"] = atlas_data[sprite_data_name]["width"]
            display_data["height"] = atlas_data[sprite_data_name]["height"]

        verts = get_mixed_vertex_data(sprite)
        vert_coords_default[sprite_name] = verts
        display_data["vertices"] = convert_vertex_data_to_pixel_space(verts)

        bm = bmesh.from_edit_mesh(sprite.data)
        display_data["userEdges"] = get_edge_data(bm,only_outer_edges=False)
        display_data["edges"] = get_edge_data(bm)
        display_data["triangles"] = get_triangle_data(bm)
        display_data["uvs"] = get_uv_data(bm)

    if armature != None:
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()

        if len(sprite.data.vertices) != 4:
            ### write mesh bone data
            weights, bones = get_bone_weight_data(self,sprite,armature)

            display_data["weights"] = weights

            display_data["bonePose"] = []
            for bone in bones:
                mat = get_bone_matrix(armature,bone["bone"],relative=False)
                display_data["bonePose"].append(bone["index"]+1)
                display_data["bonePose"].append(round(mat[0][0],3))
                display_data["bonePose"].append(round(mat[0][1],3))
                display_data["bonePose"].append(round(mat[1][0],3))
                display_data["bonePose"].append(round(mat[1][1],3))
                display_data["bonePose"].append(round(mat[1][3] * scale ,3))#pos x
                display_data["bonePose"].append(round(-mat[0][3] *scale ,3))#pos y
            armature.data.pose_position = "POSE"
            bpy.context.view_layer.update()

            w = round(sprite.matrix_local[0][0], 3)
            x = round(sprite.matrix_local[0][2], 3)
            y = round(sprite.matrix_local[2][0], 3)
            z = round(sprite.matrix_local[2][2], 3)
            sca_x = round(sprite.matrix_local.to_translation()[0]*scale, 3)
            sca_y = round(-sprite.matrix_local.to_translation()[2]*scale, 3)
            display_data["slotPose"] = [w,x,y,z, sca_x, sca_y]
        else:
            ### write sprite bone data
            bone = get_bone_with_most_influence(self, sprite)
            sprite_center_pos = get_mesh_center(sprite, 1.0)
            if bone != None:
                bone_pos = get_bone_matrix(self.armature, bone, relative=False).to_translation()
                p_bone = self.armature.pose.bones[bone.name]
                sprite_pos_final = (bone.matrix_local.inverted() @ sprite_center_pos) * scale
                angle = get_bone_angle(armature, bone, relative=False)
            else:
                sprite_pos_final = sprite_center_pos * scale
                sprite_pos_final = sprite_pos_final.zxy
                angle = 0

            display_data["transform"] = OrderedDict()
            display_data["transform"]["x"] = round(sprite_pos_final.y,3)
            display_data["transform"]["y"] = round(-sprite_pos_final.x,3)


            if angle != 0:
                display_data["transform"]["skX"] = -round(angle, 2)
                display_data["transform"]["skY"] = -round(angle, 2)
            if atlas_data[sprite_data_name]["output_scale"] != 1.0:
                display_data["transform"]["scX"] = round(1.0 / atlas_data[sprite_data_name]["output_scale"], 2)
                display_data["transform"]["scY"] = round(1.0 / atlas_data[sprite_data_name]["output_scale"], 2)

    bpy.ops.object.mode_set(mode="OBJECT")

    #bpy.data.objects.remove(sprite,do_unlink=True)
    return display_data


def get_skin_data(self,sprites,armature,scale):
    context = bpy.context

    global tex_pathes
    tex_pathes = {}

    ### skin data array
    skin_data = [{"slot":[]}]

    for sprite in sprites:
        ### create slot data
        slot_data = OrderedDict()
        slot_data["name"] = sprite.name
        slot_data["display"] = []

        if sprite.type == "MESH":
            if sprite.coa_tools.type == "MESH":
                data2 = get_skin_slot(self,sprite,armature,scale)
                slot_data["display"].append(data2)
            elif sprite.coa_tools.type == "SLOT":
                for slot in sprite.coa_tools.slot:
                    data2 = get_skin_slot(self,sprite,armature,scale,slot_data=slot.mesh)
                    slot_data["display"].append(data2)

            skin_data[0]["slot"].append(slot_data)
    return skin_data

def get_driver_bone_target(driver):
    targets = []
    for v in driver.driver.variables:
        if v.targets[0].bone_target != "":
            targets.append(v.targets[0].bone_target)
    return targets

def get_bone_matrix(armature,bone,relative=True):
    pose_bone = armature.pose.bones[bone.name]

    m = Matrix() ### inverted posebone origin matrix
    m.row[0] = [0,0,1,0]
    m.row[1] = [1,0,0,0]
    m.row[2] = [0,1,0,0]
    m.row[3] = [0,0,0,1]

    if bone.parent == None:
        mat_bone_space = m @ pose_bone.matrix
    else:
        if relative:
            #if bone.use_inherit_rotation and bone.use_inherit_scale:
            # mat_bone_space = pose_bone.parent.matrix.inverted() @ pose_bone.matrix
            mat_bone_space = pose_bone.matrix
            for parent in pose_bone.parent_recursive:
                pose_bone_matrix = parent.matrix.inverted() @ mat_bone_space
                mat_bone_space = pose_bone.parent.matrix.inverted() @ pose_bone.matrix
        else:
            mat_bone_space = m @ pose_bone.matrix
    #### remap matrix
    loc, rot, scale = mat_bone_space.decompose()

    #if not bone.use_inherit_scale:
    #    scale = (m * pose_bone.matrix).decompose()[2]

    loc_mat = Matrix.Translation(loc)

    rot_mat = rot.inverted().to_matrix().to_4x4()

    scale_mat = Matrix()
    scale_mat[0][0] = scale[1]
    scale_mat[1][1] = scale[0]
    scale_mat[2][2] = scale[2]
    mat_bone_space = loc_mat @ rot_mat @ scale_mat
    return mat_bone_space

def get_mesh_center(sprite, scale):
    average_vert = Vector((0,0,0))
    for i,vert in enumerate(sprite.data.vertices):
        average_vert += vert.co
    average_vert /= len(sprite.data.vertices)
    pos = (sprite.matrix_world @ average_vert) * scale
    pos_2d = Vector((pos[0], pos[2]))
    return pos

def get_bone_pos(armature,bone,scale,relative=True):
    loc, rot, sca = get_bone_matrix(armature, bone, relative).decompose()

    pos_2d = Vector((loc[1],-loc[0])) * scale # flip x and y and negate x to fit dragonbones coordinate system
    return pos_2d

def get_bone_angle(armature,bone,relative=True):
    loc, rot, scale = get_bone_matrix(armature,bone,relative).decompose()
    rot_x = round(math.degrees(rot.to_euler().x),2)
    rot_y = round(math.degrees(rot.to_euler().y),2)
    rot_z = -round(math.degrees(rot.to_euler().z),2)
#    if get_bone_scale(armature,bone)[0] < 0:
#        rot_z = - rot_z
    return rot_z

def get_bone_scale(armature,bone,relative=True):
    mat = get_bone_matrix(armature,bone)
    loc, rot, scale = get_bone_matrix(armature, bone, relative).decompose()
    return scale

def get_bone_data(self,armature,sprite_object,scale):

    bone_data = []
    bone_data.append(OrderedDict({"name": self.sprite_object.name})) ### append root

    for bone in armature.data.bones:
        pbone = armature.pose.bones[bone.name]
        data = {}
        data["name"] = bone.name
        data["transform"] = {}

        ### get bone position
        pos = get_bone_pos(armature,bone,scale)
        bone_default_pos[bone.name] = Vector(pos)
        if pos != Vector((0,0)):
            data["transform"]["x"] = round(pos[0], 2)
            data["transform"]["y"] = round(pos[1], 2)

        ### get bone angle    
        angle = get_bone_angle(armature,bone) if not bone_uses_constraints[pbone.name] else get_bone_angle(armature,bone,relative=False)
        bone_default_rot[bone.name] = angle
        if angle != 0:
            data["transform"]["skX"] = round(angle, 2)
            data["transform"]["skY"] = round(angle, 2)

        ### get bone scale
        sca = get_bone_scale(armature,bone) if not bone_uses_constraints[pbone.name] else get_bone_scale(armature,bone,relative=False)
        if sca != Vector((1.0,1.0,1.0)):
            data["transform"]["scX"] = round(sca[0], 2)
            data["transform"]["scY"] = round(sca[1], 2)

        if int(bone.use_inherit_rotation) != 1 or bone_uses_constraints[pbone.name]:
            data["inheritRotation"] = int(bone.use_inherit_rotation) if not bone_uses_constraints[pbone.name] else 0
        if int(bone.use_inherit_scale) != 1 or bone_uses_constraints[pbone.name]:
            data["inheritScale"] = int(bone.use_inherit_scale) if not bone_uses_constraints[pbone.name] else 0


        if bone.parent != None:
            data["parent"] = bone.parent.name
        else:
            data["parent"] = sprite_object.name
        data["length"] = int((bone.head - bone.tail).length*scale)

        bone_data.append(data)

    return bone_data

def get_bone_index(self,armature,bone_name):
    armature_bones = []
    for bone in armature.data.bones:
        armature_bones.append(bone)

    for i,bone in enumerate(armature_bones):
        if bone_name == bone.name:
            return i

### get weight data
def get_bone_weight_data(self,obj,armature):
    data = []
    bone_names = []
    bones = []
    for vert in obj.data.vertices:
        groups = []
        for group in vert.groups:
            group_name = obj.vertex_groups[group.group].name
            if group_name in armature.data.bones:
                groups.append({"group":group,"group_name":group_name})

        data.append(len(groups))
        for group in groups:
            b_index = get_bone_index(self,armature,group["group_name"])
            bone_index = b_index+1
            data.append(bone_index)
            bone_weight = round(group["group"].weight,3)
            data.append(bone_weight)

            if group["group_name"] not in bone_names:
                bone_names.append(group["group_name"])

    armature_bones = []
    for bone in armature.data.bones:
        armature_bones.append(bone)

    for i,bone in enumerate(armature_bones):
        if bone.name in bone_names:
            bone = armature.data.bones[bone.name]
            bones.append({"index":i,"bone":bone})
    return data, bones

### Export Animations
### get objs and bones that are keyed on given frame    
def bone_key_on_frame(bone,frame,animation_data,type="LOCATION"): ### LOCATION, ROTATION, SCALE, ANY
    action = animation_data.action if animation_data != None else None
    type = "."+type.lower()
    if action != None:
        for fcurve in action.fcurves:
            if bone.name in fcurve.data_path and (type in fcurve.data_path or type == ".any"):
                for keyframe in fcurve.keyframe_points:
                    if keyframe.co[0] == frame:
                        return True
    return False

def property_key_on_frame(obj,prop_names,frame,type="PROPERTY"):
    if type == "SHAPEKEY":
        obj = obj.shape_keys

    if obj != None and obj.animation_data != None:
    ### check if property has a key set
        action = obj.animation_data.action
        if action != None:
            for fcurve in action.fcurves:
                for prop_name in prop_names:
                    if prop_name in fcurve.data_path:
                        for keyframe in fcurve.keyframe_points:
                            if keyframe.co[0] == frame:
                                return True
    ### check if property has a bone driver and bone has a key set
        for driver in obj.animation_data.drivers:
            for prop_name in prop_names:
                if prop_name in driver.data_path:
                    for var in driver.driver.variables:
                        armature = var.targets[0].id
                        if armature != None:
                            bone_target = var.targets[0].bone_target
                            if bone_target in armature.data.bones:
                                bone = armature.data.bones[bone_target]
                                pbone = armature.pose.bones[bone_target]
                                key_on_frame = bone_key_on_frame(bone,frame,armature.animation_data,type="ANY")
                                if key_on_frame:
                                    return key_on_frame
                                for const in pbone.constraints:
                                    if const.type == "ACTION":
                                        bone = armature.data.bones[const.subtarget] if const.subtarget in armature.data.bones else None
                                        if bone != None:
                                            key_on_frame = bone_key_on_frame(bone,frame,armature.animation_data,type="ANY")
                                        if key_on_frame:
                                            return key_on_frame
    return False

def get_z_order(self, slot):
    slots = []
    for i,s in enumerate(self.sprites):
        if s.type == "MESH":
            slots.append(s)

    slots.sort(key=lambda x: x.coa_tools.z_value)

    for i, s in enumerate(slots):
        if i == slot.coa_tools.z_value:
            return i
    return -1



def get_animation_data(self,sprite_object,armature,armature_orig):
    context = bpy.context
    scale = 1/get_addon_prefs(context).sprite_import_export_scale
    anims = sprite_object.coa_tools.anim_collections

    animations = []

    for anim_index,anim in enumerate(anims):
        if anim.name not in ["NO ACTION","Restpose"] and anim.export:
            sprite_object.coa_tools.anim_collections_index = anim_index ### set animation

            anim_data = animation_data.copy()
            anim_data["duration"] = anim.frame_end
            anim_data["playTimes"] = 0
            anim_data["name"] = anim.name
            anim_data["bone"] = []
            anim_data["slot"] = []
            anim_data["zOrder"] = {}
            anim_data["ffd"] = []
            animation_data["frame"] = []


            ### append all slots to list
            slot_keyframe_duration = {}
            ffd_keyframe_duration = {}
            ffd_last_frame_values = {}
            z_order_defaults = {}
            for slot in self.sprites:
                if slot.type == "MESH":
                    anim_data["slot"].append({"name":slot.name,"colorFrame":[],"displayFrame":[]})
                    slot_keyframe_duration[slot.name] = {"color_duration": 0,"display_duration": 0,"z_order_duration": 0}
                    z_order_defaults[slot.name] = {"zOrder": get_z_order(self, slot)}

                    if slot.coa_tools.type == "MESH":
                        anim_data["ffd"].append({"name":slot.data.name,"slot":slot.name,"frame":[]})
                        ffd_keyframe_duration[slot.data.name] = {"ffd_duration":0}
                        ffd_last_frame_values[slot.data.name] = None
                    elif slot.coa_tools.type == "SLOT":
                        for slot2 in slot.coa_tools.slot:
                            anim_data["ffd"].append({"name":slot2.mesh.name,"slot":slot.name,"frame":[]})
                            ffd_keyframe_duration[slot2.mesh.name] = {"ffd_duration":0}
                            ffd_last_frame_values[slot2.mesh.name] = None

            ### gather timeline events

            for i, timeline_event in enumerate(anim.timeline_events):

                if i == 0:
                    if timeline_event.frame != 0:
                        anim_data["frame"].append({"duration": timeline_event.frame})

                if i < len(anim.timeline_events)-1:
                    next_event = anim.timeline_events[i+1]

                    duration = next_event.frame - timeline_event.frame
                else:
                    duration = anim.frame_end - timeline_event.frame

                event_data = {}
                event_data["duration"] = duration
                for event in timeline_event.event:
                    if event.type == "SOUND":
                        event_data["sound"] = event.value
                    elif event.type == "ANIMATION":
                        event_data["action"] = event.animation
                    elif event.type == "EVENT":
                        if "events" not in event_data:
                            event_data["events"] = []
                        custom_event = {}
                        custom_event["name"] = event.value
                        if event.target != "":
                            custom_event["bone"] = event.target
                        if event.int != "":
                            custom_event["ints"] = [int(event.int)]
                        if event.float != "":
                            custom_event["floats"] = [float(event.float)]
                        if event.string != "":
                            custom_event["strings"] = [event.string]
                        event_data["events"].append(custom_event)

                anim_data["frame"].append(event_data)

            ### check if slot has animation data. if so, store for later usage                
            SHAPEKEY_ANIMATION = {}
            for i in range(anim.frame_end+1):
                frame = anim.frame_end-i
                slot_data = None
                for slot in self.sprites:
                    if slot.type == "MESH":

                        slot_data = []
                        if slot.coa_tools.type == "MESH":
                            slot_data = [tmp_slots_data[slot.data.name]]
                        elif slot.coa_tools.type == "SLOT":
                            for slot2 in slot.coa_tools.slot:
                                slot_data.append(tmp_slots_data[slot2.mesh.name])
                if slot_data != None:
                    for item in slot_data:
                        data = item["data"]
                        data_name = item["name"]

                        key_blocks = []
                        if data.shape_keys != None:
                            for key in data.shape_keys.key_blocks:
                                key_blocks.append(key.name)
                        if property_key_on_frame(data,key_blocks,frame,type="SHAPEKEY"):
                            SHAPEKEY_ANIMATION[slot.name] = True
                            break


            ### append all bones to list
            bone_keyframe_duration = {}
            if armature != None:
                for bone in armature.data.bones:
                    anim_data["bone"].append({"name":bone.name,"translateFrame":[],"rotateFrame":[],"scaleFrame":[]})
                    bone_keyframe_duration[bone.name] = {"scale_duration":0,"rot_duration":0,"pos_duration":0,"last_scale":None, "last_rot":None, "last_pos":None}

            for i in range(anim.frame_end+1):
                frame = anim.frame_end-i
                context.scene.frame_set(frame)

                #### HANDLE SLOT ANIMATION
                j = 0
                for slot in self.sprites:
                    if slot.type == "MESH":
                        slot_keyframe_duration[slot.name]["color_duration"] += 1
                        slot_keyframe_duration[slot.name]["display_duration"] += 1
                        slot_keyframe_duration[slot.name]["z_order_duration"] += 1

                        if property_key_on_frame(slot,["coa_tools.z_value"], frame):
                            z_order_data = {}
                            z_order_data["duration"] = slot_keyframe_duration[slot.name]["z_order_duration"]
                            z_order_data["zOrder"] = []
                            for s in self.sprites:
                                if s.type == "MESH":
                                    if z_order_defaults[s.name]["zOrder"] != get_z_order(self, s):
                                        z_order_data["zOrder"].append(z_order_defaults[s.name]["zOrder"])
                                        z_order_data["zOrder"].append(get_z_order(self, s) - z_order_defaults[s.name]["zOrder"])
                            if "frame" not in anim_data["zOrder"]:
                                anim_data["zOrder"]["frame"] = []
                            anim_data["zOrder"]["frame"].insert(0, z_order_data)

                            slot_keyframe_duration[slot.name]["z_order_duration"] = 0


                        if property_key_on_frame(slot,["coa_tools.alpha","coa_tools.modulate_color"],frame):

                            keyframe_data = {}
                            keyframe_data["duration"] = slot_keyframe_duration[slot.name]["color_duration"]
                            keyframe_data["tweenEasing"] = 0
                            keyframe_data["value"] = get_modulate_color(slot)

                            anim_data["slot"][j]["colorFrame"].insert(0,keyframe_data)
                            slot_keyframe_duration[slot.name]["color_duration"] = 0

                        if property_key_on_frame(slot,["coa_tools.slot_index"],frame) or frame in [0,anim.frame_end]:
                            keyframe_data = {}
                            keyframe_data["duration"] = slot_keyframe_duration[slot.name]["display_duration"]
                            keyframe_data["value"] = slot.coa_tools.slot_index

                            anim_data["slot"][j]["displayFrame"].insert(0,keyframe_data)
                            slot_keyframe_duration[slot.name]["display_duration"] = 0


                        j += 1
                #### HANDLE BONE ANIMATION
                if armature != None:
                    for j,bone in enumerate(armature.data.bones):
                        bone_orig = armature_orig.data.bones[bone.name]
                        pose_bone_orig = armature_orig.pose.bones[bone.name]
                        const_len = len(pose_bone_orig.constraints)
                        in_ik_chain = pose_bone_orig.is_in_ik_chain

                        bone_keyframe_duration[bone.name]["scale_duration"] += 1
                        bone_keyframe_duration[bone.name]["rot_duration"] += 1
                        bone_keyframe_duration[bone.name]["pos_duration"] += 1

                        bake_anim = self.scene.coa_tools.export_bake_anim and frame%self.scene.coa_tools.export_bake_steps==0

                        ### bone position
                        if bone_key_on_frame(bone_orig,frame,armature_orig.animation_data,type="LOCATION") or frame in [0,anim.frame_end] or const_len > 0 or in_ik_chain or bake_anim:
                            bone_pos = get_bone_pos(armature,bone,scale) - self.armature_restpose[bone.name]["bone_pos"]

                            keyframe_data = {}
                            keyframe_data["duration"] = bone_keyframe_duration[bone.name]["pos_duration"]
                            keyframe_data["curve"] = [.5,0,.5,1] if bake_anim == False else [0,0,1,1]
                            keyframe_data["x"] = round(bone_pos[0],2)
                            keyframe_data["y"] = round(bone_pos[1],2)

                            if frame in [0, anim.frame_end] or (bone_keyframe_duration[bone.name]["last_pos"] != [keyframe_data["x"], keyframe_data["y"]]):
                                ### if previous keyframe differs and keyframe duration is greater 1 add an extra keyframe inbetween
                                if bone_keyframe_duration[bone.name]["pos_duration"] > 1 and bone_keyframe_duration[bone.name]["last_pos"] != [keyframe_data["x"], keyframe_data["y"]]:
                                    if const_len > 0 or in_ik_chain:
                                        keyframe_data_last = {}
                                        keyframe_data_last["duration"] = bone_keyframe_duration[bone.name]["pos_duration"]-1
                                        keyframe_data_last["curve"] = [.5, 0, .5, 1] if bake_anim == False else [0, 0, 1, 1]
                                        keyframe_data_last["x"] = bone_keyframe_duration[bone.name]["last_pos"][0]
                                        keyframe_data_last["y"] = bone_keyframe_duration[bone.name]["last_pos"][1]
                                        anim_data["bone"][j]["translateFrame"].insert(0, keyframe_data_last)

                                        keyframe_data["duration"] = 1

                                anim_data["bone"][j]["translateFrame"].insert(0, keyframe_data)
                                bone_keyframe_duration[bone.name]["pos_duration"] = 0
                                bone_keyframe_duration[bone.name]["last_pos"] = [keyframe_data["x"], keyframe_data["y"]]

                        ### bone rotation
                        if bone_key_on_frame(bone_orig,frame,armature_orig.animation_data,type="ROTATION") or frame in [0,anim.frame_end] or const_len > 0 or in_ik_chain or bake_anim:

                            # bone_rot = math.fmod(get_bone_angle(armature,bone) - self.armature_restpose[bone.name]["bone_rot"], 360)
                            if not bone_uses_constraints[bone.name]:
                                bone_rot = get_bone_angle(armature,bone, relative=True) - self.armature_restpose[bone.name]["bone_rot"]
                            else:
                                bone_rot = get_bone_angle(armature, bone, relative=False) - self.armature_restpose[bone.name]["bone_rot"]

                            if bone_rot < -180:
                                bone_rot = bone_rot + 360
                            elif bone_rot > 180:
                                bone_rot = bone_rot - 360

                            keyframe_data = {}
                            keyframe_data["duration"] = bone_keyframe_duration[bone.name]["rot_duration"]
                            keyframe_data["curve"] = [.5,0,.5,1] if bake_anim == False else [0,0,1,1]
                            keyframe_data["rotate"] = round(bone_rot, 2)

                            if (frame in [0,anim.frame_end]) or (bone_keyframe_duration[bone.name]["last_rot"] != keyframe_data["rotate"]):
                                ### if previous keyframe differs and keyframe duration is greater 1 add an extra keyframe inbetween
                                if bone_keyframe_duration[bone.name]["rot_duration"] > 1 and (bone_keyframe_duration[bone.name]["last_rot"] != keyframe_data["rotate"]):
                                    if const_len > 0 or in_ik_chain:
                                        keyframe_data_last = {}
                                        keyframe_data_last["duration"] = bone_keyframe_duration[bone.name]["rot_duration"] - 1
                                        keyframe_data_last["curve"] = [.5, 0, .5, 1] if bake_anim == False else [0, 0, 1, 1]
                                        keyframe_data_last["rotate"] = round(bone_keyframe_duration[bone.name]["last_rot"], 2)
                                        anim_data["bone"][j]["rotateFrame"].insert(0, keyframe_data_last)

                                        keyframe_data["duration"] = 1

                                anim_data["bone"][j]["rotateFrame"].insert(0, keyframe_data)
                                bone_keyframe_duration[bone.name]["rot_duration"] = 0
                                bone_keyframe_duration[bone.name]["last_rot"] = keyframe_data["rotate"]

                        ### bone scale
                        if bone_key_on_frame(bone_orig,frame,armature_orig.animation_data,type="SCALE") or frame in [0,anim.frame_end] or const_len > 0 or in_ik_chain or bake_anim:

                            bone_scale = get_bone_scale(armature,bone,relative=True) if not bone_uses_constraints[bone.name] else get_bone_scale(armature,bone,relative=False)

                            keyframe_data = {}
                            keyframe_data["duration"] = bone_keyframe_duration[bone.name]["scale_duration"]
                            keyframe_data["curve"] = [.5,0,.5,1] if bake_anim == False else [0,0,1,1]
                            keyframe_data["x"] = round(bone_scale[0],2)
                            keyframe_data["y"] = round(bone_scale[1],2)

                            if (frame in [0,anim.frame_end]) or (bone_keyframe_duration[bone.name]["last_scale"] != [keyframe_data["x"], keyframe_data["y"]]):

                                ### if previous keyframe differs and keyframe duration is greater 1 add an extra keyframe inbetween
                                if bone_keyframe_duration[bone.name]["scale_duration"] > 1 and (bone_keyframe_duration[bone.name]["last_scale"] != [keyframe_data["x"], keyframe_data["y"]]):
                                    if const_len > 0 or in_ik_chain:
                                        keyframe_data_last = {}
                                        keyframe_data_last["duration"] = bone_keyframe_duration[bone.name]["scale_duration"]-1
                                        keyframe_data_last["curve"] = [.5,0,.5,1] if bake_anim == False else [0,0,1,1]
                                        keyframe_data_last["x"] = bone_keyframe_duration[bone.name]["last_scale"][0]
                                        keyframe_data_last["y"] = bone_keyframe_duration[bone.name]["last_scale"][1]
                                        anim_data["bone"][j]["scaleFrame"].insert(0,keyframe_data_last)

                                        keyframe_data["duration"] = 1

                                anim_data["bone"][j]["scaleFrame"].insert(0,keyframe_data)
                                bone_keyframe_duration[bone.name]["scale_duration"] = 0
                                bone_keyframe_duration[bone.name]["last_scale"] = [keyframe_data["x"], keyframe_data["y"]]

                #### HANDLE FFD Transformations (Blender Shapekeys)
                j = 0
                for slot in self.sprites:
                    if slot.type == "MESH":

                        slot_data = []
                        if slot.coa_tools.type == "MESH":
                            slot_data = [tmp_slots_data[slot.data.name]]
                        elif slot.coa_tools.type == "SLOT":
                            for slot2 in slot.coa_tools.slot:
                                slot_data.append(tmp_slots_data[slot2.mesh.name])

                        for item in slot_data:
                            data = item["data"]
                            data_name = item["name"]

                            bake_anim = self.scene.coa_tools.export_bake_anim and frame%self.scene.coa_tools.export_bake_steps==0

                            if data.shape_keys != None:
                                ffd_keyframe_duration[data_name]["ffd_duration"] += 1

                                key_blocks = []
                                for key in data.shape_keys.key_blocks:
                                    key_blocks.append(key.name)
                                if property_key_on_frame(data,key_blocks,frame,type="SHAPEKEY") or (frame in [0,anim.frame_end] and data_name in SHAPEKEY_ANIMATION):# or bake_anim:
                                    ffd_data = {}
                                    ffd_data["duration"] = ffd_keyframe_duration[data_name]["ffd_duration"]
                                    ffd_data["curve"] = [.5,0,.5,1] if bake_anim == False else [0,0,1,1]
#                                    if bake_anim == False:
#                                        ffd_data["curve"] = [.5,0,.5,1]
#                                    else:
#                                        ffd_data["tweenEasing"] = 0

                                    verts = get_mixed_vertex_data(item["object"])
                                    verts_relative = []
                                    for i,co in enumerate(verts):
                                        verts_relative.append(Vector(co) - Vector(vert_coords_default[slot.name][i]))

                                    ffd_data["vertices"] = convert_vertex_data_to_pixel_space(verts_relative)

                                    if (frame in [0, anim.frame_end]) or (ffd_last_frame_values[data_name] != ffd_data["vertices"]):
                                        # ### if previous keyframe differs and keyframe duration is greater 1 add an extra keyframe inbetween
                                        # if ffd_data["duration"] > 1 and (ffd_last_frame_values[data_name] != ffd_data["vertices"]):
                                        #     ffd_data_last = {}
                                        #     ffd_data_last["duration"] = ffd_keyframe_duration[data_name]["ffd_duration"]-1
                                        #     ffd_data_last["curve"] = [.5,0,.5,1]
                                        #     ffd_data_last["vertices"] = ffd_last_frame_values[data_name]
                                        #
                                        #     anim_data["ffd"][j]["frame"].insert(0,ffd_data_last)
                                        #     ffd_data["duration"] = 1

                                        anim_data["ffd"][j]["frame"].insert(0,ffd_data)
                                        ffd_keyframe_duration[data_name]["ffd_duration"] = 0
                                        ffd_last_frame_values[data_name] = ffd_data["vertices"]
                            j += 1


            ### cleanup animation data
            delete_keys = []
            for key in anim_data:
                data = anim_data[key]
                if type(data) == list:
                    if len(data) == 0:
                        delete_keys.append(key)
                    else:
                        for item in data:
                            delete_keys2 = []
                            if type(item) == dict:
                                for key2 in item:
                                    data2 = item[key2]
                                    if type(data2) == list:
                                        if len(data2) == 0:
                                            #del item[key2]
                                            delete_keys2.append(key2)
                            for key2 in delete_keys2:
                                del item[key2]
            for key in delete_keys:
                del anim_data[key]

            animations.append(anim_data)
    return animations


class COATOOLS_OT_DragonBonesExport(bpy.types.Operator):
    bl_idname = "coa_tools.export_dragon_bones"
    bl_label = "Dragonbones Export"
    bl_description = ""
    bl_options = {"REGISTER"}

    reduce_size: BoolProperty(default=False)

    sprite_object = None
    armature = None
    sprites = None
    scale = 0.0

    armature_restpose = {}

    json_data = {}

    @classmethod
    def poll(cls, context):
        return True

    def __init__(self):
        self.reduce_size = bpy.context.scene.coa_tools.minify_json
        self.sprite_scale = bpy.context.scene.coa_tools.sprite_scale

    def draw(self,context):
        layout = self.layout
        col = layout.column()
        col.prop(self,"bake_anim",text="Bake Animation")
        if self.bake_anim:
            col.prop(self,"bake_interval",text="Bake Interval")
        col.prop(self,"reduce_size",text="Reduce Export Size")

        if self.generate_atlas:
            box = col.box()
        else:
            box = col
        box.prop(self,"generate_atlas",text="Generate Texture Atlas")
        if self.generate_atlas:
            row = box.row()
            #row.prop(self,"atlas_size",text="Atlas Size",expand=True)
            if self.atlas_size == "MANUAL":
                row = box.row()
                row.prop(self,"atlas_dimension",text="")
            row = box.row()
            row.prop(self,"unwrap_method",text="Unwrap Method",expand=True)
            row = box.row()
            row.prop(self,"island_margin",text="Sprite Margin")

    def get_init_state(self,context):
        self.selected_objects = context.selected_objects[:]
        self.active_object = context.active_object
        self.sprite_object = get_sprite_object(context.active_object)

        self.animation_index = self.sprite_object.coa_tools.anim_collections_index
        self.frame_current = context.scene.frame_current

    def set_init_state(self,context):
        for obj in context.scene.objects:
            if obj in self.selected_objects:
                obj.select_set(True)
            else:
                obj.select_set(False)
        context.view_layer.objects.active = self.active_object

        if len(self.sprite_object.coa_tools.anim_collections) > 0:
            self.sprite_object.coa_tools.anim_collections_index = self.animation_index
        context.scene.frame_current = self.frame_current

    def execute(self, context):
        bpy.ops.ed.undo_push(message="Export to Dragonbones")
        global tmp_slots_data
        tmp_slots_data = {}

        self.get_init_state(context)
        self.scene = context.scene

        ### set animation mode to action
        coa_nla_mode = str(self.scene.coa_tools.nla_mode)
        self.scene.coa_tools.nla_mode = "ACTION"


        ### get sprite object, sprites and armature
        self.scale = 1/get_addon_prefs(context).sprite_import_export_scale
        self.sprite_object = get_sprite_object(context.active_object)
        self.armature_orig = get_armature(self.sprite_object)

        self.sprites = get_children(context,self.sprite_object,[])
        self.sprites = sorted(self.sprites, key=lambda obj: obj.location[1], reverse=True) ### sort objects based on the z depth. needed for draw order

        self.armature = create_cleaned_armature_copy(self,self.armature_orig,self.sprites) ### create a cleaned copy of the armature that contains only deform bones and which has applied copy transform constraints

        ### get export, project and json path
        export_path = bpy.path.abspath(self.scene.coa_tools.export_path)
        texture_dir_path = os.path.join(export_path , self.scene.coa_tools.project_name+"_texture")
        json_path = os.path.join(export_path,self.scene.coa_tools.project_name+"_ske.json")

        ### check if export dir exists
        if not os.path.exists(export_path):
            self.report({"WARNING"},"Export Path does not exists. Set a valid Export Path.")
            return{'CANCELLED'}


        ### export texture atlas
        if self.scene.coa_tools.export_image_mode == "ATLAS":
            sprites = [sprite for sprite in self.sprites if sprite.type == "MESH"]
            if len(sprites) > 0:
                generate_texture_atlas(self, sprites,self.scene.coa_tools.project_name,export_path,
                                       img_width=self.scene.coa_tools.atlas_resolution_x,
                                       img_height=self.scene.coa_tools.atlas_resolution_y,
                                       sprite_scale=self.scene.coa_tools.sprite_scale,
                                       margin=self.scene.coa_tools.atlas_island_margin)

        ### create texture directory
        if self.scene.coa_tools.export_image_mode == "IMAGES":
            if os.path.exists(texture_dir_path):
                shutil.rmtree(texture_dir_path)
            os.makedirs(texture_dir_path)

        ### copy all textures to texture directory
        copy_textures(self,self.sprites,texture_dir_path)

        ### create json data
        if self.armature != None:
            self.armature.data.pose_position = "REST"
            self.armature_orig.data.pose_position = "REST"

        self.json_data = setup_json_project(self.scene.coa_tools.project_name) ### create base template
        self.json_data["armature"] =  [setup_armature_data(self.sprite_object, self.scene.coa_tools.armature_name)] ### create base armature
        self.json_data["armature"][0]["frameRate"] = self.scene.render.fps
        self.json_data["armature"][0]["slot"] = get_slot_data(self,self.sprites)
        self.json_data["armature"][0]["skin"] = get_skin_data(self,self.sprites,self.armature,self.scale)
        self.json_data["armature"][0]["bone"] = get_bone_data(self,self.armature,self.sprite_object,self.scale) if self.armature != None else [{"name":self.sprite_object.name}]

        if self.armature != None:
            self.armature.data.pose_position = "POSE"
            self.armature_orig.data.pose_position = "POSE"
        self.json_data["frameRate"] = self.scene.render.fps
        self.json_data["armature"][0]["animation"] = get_animation_data(self,self.sprite_object,self.armature,self.armature_orig)

        ### write and store json file
        if self.reduce_size:
            json_file = json.dumps(self.json_data,separators=(',',':'))
        else:
            json_file = json.dumps(self.json_data, indent="\t", sort_keys=False)

        text_file = open(json_path, "w")
        text_file.write(json_file)
        text_file.close()




        ### cleanup scene
        self.set_init_state(context) ### restore initial object selection
        if self.armature != None:
            bpy.data.objects.remove(self.armature) ### delete copied armature

        for key in tmp_slots_data:
            bpy.data.objects.remove(tmp_slots_data[key]["object"], do_unlink=True)

        self.scene.coa_tools.nla_mode = coa_nla_mode

        # cleanup scene and add an undo history step
        bpy.ops.ed.undo_push(message="Export Creature")
        bpy.ops.ed.undo()
        bpy.ops.ed.undo_push(message="Export Creature")

        self.report({"INFO"},"Export successful.")
        return {"FINISHED"}


class COATOOLS_PT_ExportPanel(bpy.types.Panel):
    bl_idname = "COATOOLS_PT_export_panel"
    bl_label = "COA Export Panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

    def draw(self, context):

        layout = self.layout
        self.scene = context.scene

        col = layout.column()
        col.prop(self.scene.coa_tools, "project_name", text="Project Name")
        col.prop(self.scene.coa_tools, "armature_name", text="Armature Name")
        col.prop(self.scene.coa_tools, "export_path", text="Export Path")

        col = layout.column(align=True)
        row = col.row()
        row.prop(self.scene.coa_tools, "runtime_format", expand=True)

        box = col.box()

        box_col = box.column()
        box_col.label(text="Atlas Settings:")
        row = box_col.row()
        row.prop(self.scene.coa_tools, "atlas_mode", expand=True)
        subcol = box_col.column(align=True)
        subcol.prop(self.scene.coa_tools, "sprite_scale", slider=True)
        if self.scene.coa_tools.atlas_mode == "LIMIT_SIZE":
            subcol.prop(self.scene.coa_tools, "atlas_resolution_x", text="X")
            subcol.prop(self.scene.coa_tools, "atlas_resolution_y", text="Y")
        subcol.prop(self.scene.coa_tools, "atlas_island_margin")
        # subcol.prop(self.scene.coa_tools, "export_texture_bleed")
        subcol.prop(self.scene.coa_tools, "export_square_atlas")

        box_col.label(text="Data Settings:")
        subrow = box_col.row(align=True)
        if self.scene.coa_tools.runtime_format == "DRAGONBONES":
            subrow.prop(self.scene.coa_tools, "export_bake_anim")
            if self.scene.coa_tools.export_bake_anim:
                subrow.prop(self.scene.coa_tools, "export_bake_steps")
        box_col.prop(self.scene.coa_tools, "minify_json")
        box_col.prop(self.scene.coa_tools, "armature_scale")

        if self.scene.coa_tools.runtime_format == "CREATURE":
            op = col.operator("coa_tools.export_creature", text="Export")
            op.export_path = self.scene.coa_tools.export_path
            op.project_name = str(self.scene.coa_tools.project_name).lower()

        elif self.scene.coa_tools.runtime_format == "DRAGONBONES":
            op = col.operator("coa_tools.export_dragon_bones", text="Export")



def generate_texture_atlas(self, sprites, atlas_name, img_path, img_width=512, img_height=1024, sprite_scale=1.0, margin=1):
    global atlas_data
    atlas_data = {}

    context = bpy.context

    ### deselect all objects
    for obj in context.scene.objects:
        obj.select_set(False)

    ### get a list of all sprites and containing slots    
    slots = []
    for sprite in sprites:
        if sprite.type == "MESH":
            if sprite.coa_tools.type == "MESH":
                slots.append({"sprite":sprite,"slot":sprite.data})
            elif sprite.coa_tools.type == "SLOT":
                for i,slot in enumerate(sprite.coa_tools.slot):
                    slots.append({"sprite":sprite,"slot":slot.mesh})

    ### loop over all slots and create an object with slot assigned
    for slot in slots:
        dupli_sprite = slot["sprite"].copy()
        dupli_sprite.data = slot["slot"].copy()
        context.collection.objects.link(dupli_sprite)
        dupli_sprite.hide_set(False)
        dupli_sprite.select_set(True)
        context.view_layer.objects.active = dupli_sprite

        ### delete shapekeys
        if dupli_sprite.data.shape_keys != None:
            shapekeys = dupli_sprite.data.shape_keys.key_blocks
            for i in range(len(shapekeys)):
                shapekeys = dupli_sprite.data.shape_keys.key_blocks
                dupli_sprite.shape_key_remove(shapekeys[len(shapekeys)-1])
        ### apply/delete modifieres
        for modifier in dupli_sprite.modifiers:
            if modifier.name == "coa_base_sprite" and modifier.type == "MASK":
                if len(dupli_sprite.data.vertices) > 4:
                    modifier.invert_vertex_group = True
                    with bpy.context.temp_override(object=dupli_sprite, active_object=dupli_sprite):
                        if b_version_smaller_than((2,90,0)):
                            bpy.ops.object.modifier_apply(apply_as="DATA", modifier=modifier.name)
                        else:
                            bpy.ops.object.modifier_apply(modifier=modifier.name)
        for modifier in dupli_sprite.modifiers:
            dupli_sprite.modifiers.remove(modifier)

        ### delete vertex_groups
        for group in dupli_sprite.vertex_groups:
            dupli_sprite.vertex_groups.remove(group)

        ### assign mesh as vertex group    
        dupli_sprite.vertex_groups.new(name=slot["slot"].name)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='SELECT')
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        with bpy.context.temp_override(area=area, edict_object=dupli_sprite, active_object=dupli_sprite, object=dupli_sprite, region=region):
                            bpy.ops.object.vertex_group_assign()
                        break

        bpy.ops.object.mode_set(mode="OBJECT")

    img_atlas, tex_atlas_obj, atlas = TextureAtlasGenerator.generate_uv_layout(
        name="COA_UV_ATLAS",
        objects=context.selected_objects,
        width=2,
        height=2,
        max_width=img_width,
        max_height=img_height,
        margin=self.scene.coa_tools.atlas_island_margin,
        texture_bleed=self.scene.coa_tools.export_texture_bleed,
        square=self.scene.coa_tools.export_square_atlas,
        output_scale=self.sprite_scale
    )

    img_width = atlas.width
    img_height = atlas.height

    ### get uv coordinates
    bpy.ops.object.mode_set(mode="EDIT")

    bm = bmesh.from_edit_mesh(tex_atlas_obj.data)
    uv_layer = bm.loops.layers.uv["COA_UV_ATLAS"]


    sprite_data = []

    for group in tex_atlas_obj.vertex_groups:
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        override = context.copy()
                        with bpy.context.temp_override(area=area, edit_object=tex_atlas_obj, active_object=tex_atlas_obj, object=tex_atlas_obj, region=region):
                            bpy.ops.object.vertex_group_set_active(group=group.name)
                            bpy.ops.mesh.select_all(action='DESELECT')
                            bpy.ops.object.vertex_group_select()
                        break
        bmesh.update_edit_mesh(tex_atlas_obj.data)
        x = 1.0
        y = 1.0
        width = 0.0
        height = 0.0
        for vert in bm.verts:
            if vert.select:
                uv = uv_from_vert_first(uv_layer,vert)
                x = min(uv[0], x)
                y = min(1 - uv[1], y)
                width = max(uv[0], width)
                height = max(1 - uv[1], height)
        width = width - x
        height = height - y

        x_px = int(img_width*x)
        y_px = int(img_height*y)
        width_px = abs(int(img_width*width))
        height_px = abs(int(img_height*height))

        sprite = {}
        sprite["name"] = group.name
        sprite["x"] = x_px
        sprite["y"] = y_px
        sprite["width"] = width_px
        sprite["height"] = height_px
        sprite_data.append(sprite)
        atlas_data[group.name] = {"width": width_px, "height": height_px, "output_scale":atlas.output_scale}

    bpy.ops.object.mode_set(mode="OBJECT")
    ### collect sprite atlas data
    texture_atlas = {}
    texture_atlas["width"] = img_width
    texture_atlas["height"] = img_height
    texture_atlas["imagePath"] = atlas_name + "_tex.png"
    texture_atlas["name"] = self.scene.coa_tools.project_name
    texture_atlas["SubTexture"] = sprite_data

    if self.reduce_size:
        json_file = json.dumps(texture_atlas,separators=(',',':'))
    else:
        json_file = json.dumps(texture_atlas, indent="\t", sort_keys=False)

    json_path = os.path.join(img_path,atlas_name+"_tex.json")
    text_file = open(json_path, "w")
    text_file.write(json_file)
    text_file.close()

    compression_rate = int(context.scene.render.image_settings.compression)
    context.scene.render.image_settings.compression = 85
    texture_path = os.path.join(img_path,atlas_name+"_tex.png")
    img_atlas.save_render(texture_path)
    context.scene.render.image_settings.compression = compression_rate


    bpy.data.objects.remove(tex_atlas_obj, do_unlink=True)