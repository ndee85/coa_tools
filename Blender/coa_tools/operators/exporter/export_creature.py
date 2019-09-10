
'''
Copyright (C) 2019 Andreas Esau
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
from . export_helper import *
import math
from mathutils import Vector,Matrix, Quaternion, Euler
import shutil
from . texture_atlas_generator import TextureAtlasGenerator
import zipfile

class Sprite:
    def __init__(self, mesh_object):
        self.context = bpy.context
        self.name = mesh_object.name
        self.slots = []
        self.object = self.create_sprite(mesh_object)

    def create_sprite(self, mesh_object):
        # duplicate original object
        sprite = mesh_object.copy()
        sprite.name = mesh_object.name + "_EXPORT"
        if mesh_object.coa_tools.type == "SLOT":
            for slot in mesh_object.coa_tools.slot:
                slot_data = {"slot": slot.mesh.copy(),
                             "start_pt_index": None,
                             "end_pt_index": None,
                             "start_index": None,
                             "end_index": None}
                self.slots.append(slot_data)
                sprite.data = slot_data["slot"]
        else:
            slot_data = {"slot": sprite.data.copy(),
                         "start_pt_index": None,
                         "end_pt_index": None,
                         "start_index": None,
                         "end_index": None}
            self.slots = [slot_data]
            sprite.data = slot_data["slot"]
        self.context.collection.objects.link(sprite)

        # cleanup basesprite
        for slot_data in self.slots:
            slot = slot_data["slot"]
            sprite.data = slot
            if len(sprite.data.vertices) > 4:
                remove_base_sprite(sprite)
        return sprite

    def delete_sprite(self, collection):
        collection.objects.unlink(self.object)
        bpy.data.objects(self.object, do_unlink=True)
        del self

class COATOOLS_OT_CreatureExport(bpy.types.Operator):
    bl_idname = "coa_tools.export_creature"
    bl_label = "Creature Export"
    bl_description = ""
    bl_options = {"REGISTER"}

    minify_json: BoolProperty(name="Minify Json", default=True, description="Writes Json data in one line to reduce export size.")
    export_path: StringProperty(name="Export Path", default="", description="Creature Export Path.")
    project_name: StringProperty(name="Project Name", default="", description="Creature Project Name")

    def __init__(self):
        self.json_data = self.setup_json_data()
        self.texture_export_scale = 1.0
        self.armature_export_scale = 1.0
        self.sprite_object = None
        self.armature_orig = None
        self.armature = None
        self.sprite_data = []
        self.reduce_size = False
        self.scene = None
        self.init_bone_positions = {}

        self.export_progress_total = 0
        self.export_progress_current = 0

        self.root_bone_name = "__Creature RootBone__"

        self.bone_weights = {}
        self.bone_scaled = {}
        self.mesh_deformed = {}
        self.remapped_indices = {}
        self.export_path_abs = bpy.path.abspath(self.export_path)

    def setup_json_data(self):
        json_data = OrderedDict()

        json_data["mesh"] = OrderedDict()
        json_data["mesh"]["points"] = []
        json_data["mesh"]["uvs"] = []
        json_data["mesh"]["indices"] = []
        json_data["mesh"]["regions"] = OrderedDict()

        json_data["skeleton"] = OrderedDict()
        json_data["animation"] = OrderedDict()
        json_data["uv_swap_items"] = OrderedDict()
        json_data["anchor_points_items"] = {"AnchorPoints": []}

        return json_data

    def create_cleaned_armature_copy(self, context, armature_orig):
        armature = armature_orig

        selected_objects = bpy.context.selected_objects[:]
        active_object = bpy.context.active_object
        for ob in selected_objects:
            ob.select_set(False)
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="EDIT")
        for bone in armature.data.edit_bones:
            self.init_bone_positions[bone.name] = {"head": Vector(bone.head), "tail": Vector(bone.tail)}

        bpy.ops.object.mode_set(mode="OBJECT")
        for ob in context.selected_objects:
            ob.select_set(False)
        for ob in selected_objects:
            ob.select_set(True)
        context.view_layer.objects.active = active_object
        return armature

    def prepare_armature_and_sprites_for_export(self, context, scene):
        # get sprites that get exported
        sprites = []
        sprite_object_children = get_children(context, self.sprite_object, [])
        for child in sprite_object_children:
            if child.type == "MESH" and child.visible_get():
                sprite = Sprite(child)
                if len(sprite.object.data.vertices) > 3:
                    sprites.append(sprite)
        sprites = sorted(sprites, key=lambda sprite: sprite.object.location[1], reverse=False)
        armature = self.create_cleaned_armature_copy(context, self.armature_orig)
        armature.data.pose_position = "POSE"
        return sprites, armature

    def get_vertices_from_v_group(self, bm, obj, v_group="", vert_type="BMESH"): # vert_type = ["BMESH", "MESH"]
        vertices = []
        if v_group not in obj.vertex_groups:
            return vertices

        group_index = obj.vertex_groups[v_group].index
        for bm_vert in bm.verts:
            vert = obj.data.vertices[bm_vert.index]
            for group in vert.groups:
                if group.group == group_index:
                    if vert_type == "BMESH":
                        vertices.append(bm_vert)
                    elif vert_type == "MESH":
                        vertices.append(vert)
        return vertices

    def get_init_vert_pos(self, obj, vert):
        if obj.data.shape_keys:
            return obj.data.shape_keys.key_blocks[0].data[vert.index].co
        else:
            return vert.co

    def get_uv_from_vert_first(self, uv_layer, v):
        bpy.context.tool_settings.use_uv_select_sync = True
        for l in v.link_loops:
            uv_data = l[uv_layer]
            return uv_data.uv
        return None

    def get_sprite_data_by_name(self, name):
        sprite_name = name
        slot_index = 0
        if "_COA_SLOT_" in name:
            sprite_name = name.split("_COA_SLOT_")[0]
            slot_index = int(name.split("_COA_SLOT_")[1])
        for sprite in self.sprite_data:
            if sprite.name == sprite_name:
                return sprite, sprite.slots[slot_index]
        return None, None

    def check_mesh_deformation(self, context):
        anim_collections = self.sprite_object.coa_tools.anim_collections
        mesh_deformed = {}
        for anim_index, anim in enumerate(anim_collections):
            if anim.name not in ["NO ACTION", "Restpose"]:
                for sprite in self.sprite_data:
                    for i, slot in enumerate(sprite.slots):
                        sprite_name = sprite.name if len(sprite.slots) <= 1 else sprite.name + "_" + str(i).zfill(3)
                        sprite.object.data = slot["slot"]

                        mesh_contains_shapekeys = False
                        mesh_is_scaled = False

                        if sprite.object.data.shape_keys != None and len(sprite.object.data.shape_keys.key_blocks) > 1:
                            mesh_contains_shapekeys = True
                        if anim.name in self.bone_scaled:
                            for bone_name in self.bone_scaled[anim.name]:
                                if bone_name in sprite.object.vertex_groups:
                                    mesh_is_scaled = True
                                    break

                        if mesh_contains_shapekeys or mesh_is_scaled:
                            if anim.name not in mesh_deformed:
                                mesh_deformed[anim.name] = []
                            mesh_deformed[anim.name].append(sprite_name)
        return mesh_deformed



    def check_and_store_bone_scaling(self, context):
        anim_collections = self.sprite_object.coa_tools.anim_collections
        bone_scaled = {}
        for anim_index, anim in enumerate(anim_collections):
            if anim.name not in ["NO ACTION", "Restpose"]:
                self.sprite_object.coa_tools.anim_collections_index = anim_index  ### set animation

                for frame in range(anim.frame_end+1):
                    context.scene.frame_set(frame)
                    for bone in self.armature.pose.bones:
                        bone_scale = bone.matrix.to_scale()
                        bone_scale = Vector((round(bone_scale.x,1), round(bone_scale.y,1), round(bone_scale.z,1)))
                        if bone_scale != Vector((1, 1, 1)):
                            if anim.name not in bone_scaled:
                                bone_scaled[anim.name] = []
                            bone_scaled[anim.name].append(bone.name)
        return bone_scaled


    def store_bone_weights(self):
        bone_weights = {}
        for sprite in self.sprite_data:
            for i, slot in enumerate(sprite.slots):
                sprite_name = sprite.name if len(sprite.slots) <= 1 else sprite.name + "_" + str(i).zfill(3)

                sprite.object.data = slot["slot"]

                for bone in self.armature.data.bones:
                    for vert in slot["slot"].vertices:
                        weight = self.get_bone_weight(sprite.object, vert, bone)
                        if weight > 0:
                            if sprite_name not in bone_weights:
                                bone_weights[sprite_name] = {bone.name:{}}
                            elif bone.name not in bone_weights[sprite_name]:
                                bone_weights[sprite_name][bone.name] = {}
                            bone_weights[sprite_name][bone.name][str(vert.index)] = weight
        return bone_weights

    def get_bone_weight(self, obj, vert, bone):
        if bone.name not in obj.vertex_groups:
            return 0.0
        else:
            v_group = obj.vertex_groups[bone.name]
            for group in vert.groups:
                group_name = obj.vertex_groups[group.group].name

                if group_name == v_group.name:
                    return group.weight
        return 0

    def lerp(self, val1, val2, interpolation):
        return val1 * (1 - interpolation) + val2 * interpolation

    def scale_verts_by_bone(self, pbone, armature, mesh_object, vert_co, weight=1.0):
        # verts = mesh_object.data.vertices
        bone = armature.data.bones[pbone.name]
        bone_head = self.init_bone_positions[bone.name]["head"]
        bone_tail = self.init_bone_positions[bone.name]["tail"]
        bone_axis_x = (bone_tail - bone_head).normalized().xz
        bone_axis_y = bone_axis_x.orthogonal().normalized()

        world_axis_x = Vector((bone_axis_x.dot(Vector((1, 0))), bone_axis_y.dot(Vector((1, 0)))))
        world_axis_y = Vector((bone_axis_x.dot(Vector((0, 1))), bone_axis_y.dot(Vector((0, 1)))))

        bone_system_origin = (mesh_object.matrix_world.inverted() @ (armature.matrix_world @ bone_head)).xz

        bone_scale = pbone.matrix.to_scale()
        bone_scale_2d = Vector(( self.lerp( 1.0, bone_scale.y, weight), self.lerp(1.0, bone_scale.x, weight) ))

        vert_delta_co = vert_co.xz
        vert_delta_co -= bone_system_origin
        vert_delta_co = Vector((bone_axis_x.dot(vert_delta_co), bone_axis_y.dot(vert_delta_co)))
        vert_delta_co = Vector((vert_delta_co.x * bone_scale_2d.x, vert_delta_co.y * bone_scale_2d.y))
        vert_delta_co = Vector((world_axis_x.dot(vert_delta_co), world_axis_y.dot(vert_delta_co)))
        vert_delta_co += bone_system_origin

        scaled_vert_co = Vector((vert_delta_co.x, 0, vert_delta_co.y))
        return scaled_vert_co

    def get_shapekey_vert_data(self, obj, obj_name, verts, anim, relative=True):
        default_vert_positions = []
        verts = sorted(verts, key=lambda vert: vert.index, reverse=False)
        for i,vert in enumerate(verts):
            default_vert_positions.append(obj.matrix_world @ vert.co)

        verts = []
        index = int(obj.active_shape_key_index)
        shape_key = obj.shape_key_add(name="tmp_mixed_mesh", from_mix=True)
        for i, vert in enumerate(default_vert_positions):
            # shapekey_vert = obj.matrix_world @ shape_key.data[i].co
            shapekey_vert = shape_key.data[i].co
            # scale bones only when vert has bone weights and bone is scaled at any time in animation
            if obj_name in self.bone_weights:
                for bone_name in self.bone_weights[obj_name]:
                    bone = self.armature.pose.bones[bone_name]
                    if anim.name in self.bone_scaled and bone.name in self.bone_scaled[anim.name] and bone.name in obj.vertex_groups:
                        if str(i) in self.bone_weights[obj_name][bone.name]:
                            bone_weight = self.bone_weights[obj_name][bone.name][str(i)]
                            scaled_vert = self.scale_verts_by_bone(bone, self.armature, obj, shapekey_vert, bone_weight)
                            shapekey_vert = scaled_vert
            shapekey_vert = (obj.matrix_world @ shapekey_vert)

            if relative:
                offset = (shapekey_vert - vert) * self.armature_export_scale
            else:
                offset = shapekey_vert * self.armature_export_scale
            verts.append(round(offset.x, 3))
            verts.append(round(offset.z, 3))
        obj.shape_key_remove(shape_key)
        obj.active_shape_key_index = index

        return verts

    def create_dupli_atlas_objects(self, context):
        atlas_objects = []

        # deselect any selected object
        for ob in bpy.context.selected_objects:
            ob.select_set(False)

        for sprite in self.sprite_data:
            meshes = []
            for i, slot_data in enumerate(sprite.slots):
                slot = slot_data["slot"]
                atlas_sprite = sprite.object.copy()
                atlas_sprite.data = slot.copy()
                context.collection.objects.link(atlas_sprite)
                atlas_sprite.select_set(True)
                context.view_layer.objects.active = atlas_sprite
                name = sprite.name + "_COA_SLOT_" + str(i).zfill(3) if len(sprite.slots) > 1 else sprite.name
                meshes.append({"obj": atlas_sprite, "name": name})
                atlas_sprite["coa_tools.sprite_object_name"] = sprite.object.name

            for mesh_data in meshes:
                atlas_sprite = mesh_data["obj"]
                name = mesh_data["name"]
                for v_group in atlas_sprite.vertex_groups:
                    if v_group.name not in self.armature.data.bones:
                        atlas_sprite.vertex_groups.remove(v_group)
                    else:
                        v_group.name = "BONE_VGROUP_" + v_group.name
                verts = []
                for vert in atlas_sprite.data.vertices:
                    verts.append(vert.index)
                v_group = atlas_sprite.vertex_groups.new(name=name)
                v_group.add(verts, 1.0, "ADD")
                atlas_objects.append(atlas_sprite)

        # select newely created objects
        # atlas_objects = sorted(atlas_objects, key=lambda sprite: sprite.location[1], reverse=True)
        for ob in atlas_objects:
            ob.select_set(True)
            context.view_layer.objects.active = ob
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
            bpy.ops.object.mode_set(mode="OBJECT")
        context.scene.cursor.location = self.armature.matrix_world.to_translation()
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        return atlas_objects

    def get_uv_dimensions(self, bm, verts, uv_layer):
        ### first get the total dimensions of the uv
        left = 0
        top = 0
        bottom = 1
        right = 1
        for vert in verts:
            uv_first = self.get_uv_from_vert_first(uv_layer, vert)
            for i, val in enumerate(uv_first):
                if i == 0:
                    left = max(left, val)
                    right = min(right, val)
                else:
                    top = max(top, val)
                    bottom = min(bottom, val)
        height = top - bottom
        width = left - right
        return {"width": width, "height": height}

    def create_mesh_data(self, context, merged_atlas_obj):
        points = []
        uvs = []
        indices = []

        context.view_layer.objects.active = merged_atlas_obj

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

        current_face_index = 0

        vertex_index = 0

        self.sprite_data.reverse()
        for sprite in self.sprite_data:
            for j, slot in enumerate(sprite.slots):
                sprite.object.data = slot["slot"]
                v_group_name = sprite.name if len(sprite.slots) <= 1 else sprite.name + "_COA_SLOT_" + str(j).zfill(3)
                v_group = merged_atlas_obj.vertex_groups[v_group_name]

                bm = bmesh.from_edit_mesh(merged_atlas_obj.data)

                sprite, slot = self.get_sprite_data_by_name(v_group.name)

                uv_layer = bm.loops.layers.uv.active
                vertices = self.get_vertices_from_v_group(bm, merged_atlas_obj, v_group.name)
                vertices.sort(key=lambda v: v.index)

                start_pt_index = float("inf")
                end_pt_index = 0

                uv_dimensions = self.get_uv_dimensions(bm, vertices, uv_layer)
                merged_atlas_obj[v_group.name] = uv_dimensions

                for i, vert in enumerate(bm.verts):
                    if vert in vertices:
                        start_pt_index = min(vertex_index, start_pt_index)
                        end_pt_index = max(vertex_index, end_pt_index)
                        slot["start_pt_index"] = start_pt_index
                        slot["end_pt_index"] = end_pt_index

                        # get point data
                        coords = self.get_init_vert_pos(merged_atlas_obj, vert)
                        coords = (coords).xzy * self.armature_export_scale
                        points.append(round(coords.x, 3))
                        points.append(round(coords.y, 3))


                        # get uv data
                        uv = self.get_uv_from_vert_first(uv_layer, vert)
                        uvs.append(round(uv[0], 3))
                        uvs.append(round(uv[1] + 1 - uv[1]*2, 3))
                        self.remapped_indices[vert.index] = vertex_index
                        vertex_index += 1

                # get indices data
                for j, face in enumerate(bm.faces):
                    if j == 0:
                        slot["start_index"] = current_face_index
                    for vert in face.verts:
                        if vert in vertices:
                            current_face_index += 1
                            indices.append(self.remapped_indices[vert.index])
                        slot["end_index"] = current_face_index


        bpy.ops.object.mode_set(mode="OBJECT")
        return points, uvs, indices

    def create_region_data(self, context, merged_atlas_obj):
        regions = OrderedDict()

        context.view_layer.objects.active = merged_atlas_obj
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(merged_atlas_obj.data)

        region_id = 0
        for sprite in self.sprite_data:
            for i, slot in enumerate(sprite.slots):
                sprite.object.data = slot["slot"]
                name = sprite.name if len(sprite.slots) <= 1 else sprite.name + "_" + str(i).zfill(3)
                regions[name] = OrderedDict()
                regions[name]["start_pt_index"] = slot["start_pt_index"]
                regions[name]["end_pt_index"] = slot["end_pt_index"]
                regions[name]["start_index"] = slot["start_index"]
                regions[name]["end_index"] = slot["end_index"]
                regions[name]["id"] = region_id
                regions[name]["weights"] = OrderedDict()

                # get root bone weights
                for vert in slot["slot"].vertices:
                    if self.root_bone_name not in regions[name]["weights"]:
                        regions[name]["weights"][self.root_bone_name] = []
                    regions[name]["weights"][self.root_bone_name].append(0)

                slot_name = sprite.name + "_COA_SLOT_" + str(i).zfill(3) if len(sprite.slots) > 1 else sprite.name
                vertices = self.get_vertices_from_v_group(bm, merged_atlas_obj, slot_name, vert_type="MESH")

                for bone in self.armature.data.bones:
                    bone_v_group_name = "BONE_VGROUP_"+bone.name
                    regions[name]["weights"][bone.name] = []
                    for i, vert in enumerate(vertices):
                        regions[name]["weights"][bone.name].append(0)
                        for group in vert.groups:
                            v_group_name = merged_atlas_obj.vertex_groups[group.group].name
                            if v_group_name == bone_v_group_name:
                                vert_index = self.remapped_indices[vert.index] - slot["start_pt_index"]
                                regions[name]["weights"][bone.name][vert_index] = round(group.weight, 3)

                region_id += 1
        bpy.ops.object.mode_set(mode="OBJECT")
        return regions

    def create_skeleton_data(self):
        self.armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
        skeleton = OrderedDict()
        for i, pbone in enumerate(self.armature.pose.bones):
            pbone["id"] = i+1

        skeleton[self.root_bone_name] = OrderedDict()
        skeleton[self.root_bone_name]["name"] = self.root_bone_name
        skeleton[self.root_bone_name]["id"] = 0
        skeleton[self.root_bone_name]["restParentMat"] = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        skeleton[self.root_bone_name]["localRestStartPt"] = [-0.01, 0]
        skeleton[self.root_bone_name]["localRestEndPt"] = [0, 0]
        skeleton[self.root_bone_name]["children"] = []
        for pbone in self.armature.pose.bones:
            if pbone.parent == None:
                skeleton[self.root_bone_name]["children"].append(pbone["id"])


        for pbone in self.armature.pose.bones:
            skeleton[pbone.name] = OrderedDict()
            skeleton[pbone.name]["name"] = pbone.name
            skeleton[pbone.name]["id"] = pbone["id"]
            skeleton[pbone.name]["restParentMat"] = self.get_bone_parent_mat(pbone)
            head = self.get_bone_head_tail(pbone)["head"]
            tail = self.get_bone_head_tail(pbone)["tail"]
            skeleton[pbone.name]["localRestStartPt"] = [round(head.x, 3), round(head.y, 3)]
            skeleton[pbone.name]["localRestEndPt"] = [round(tail.x, 3), round(tail.y, 3)]
            skeleton[pbone.name]["children"] = []
            for child in pbone.children:
                skeleton[pbone.name]["children"].append(child["id"])
        self.armature.data.pose_position = "POSE"
        return skeleton

    # gets head and tail of a bone in either normal or local space of it's parent bone
    def get_bone_head_tail(self, pbone, local=True):
        parent_x_axis = Vector((1, 0))
        parent_y_axis = Vector((0, 1))
        space_origin = Vector((0, 0))
        if pbone.parent != None and local:
            parent_x_axis = (pbone.parent.tail.xz - pbone.parent.head.xz).normalized()
            parent_y_axis = parent_x_axis.orthogonal().normalized()
            space_origin = pbone.parent.tail.xz

        head = pbone.head.xz - space_origin
        tail = pbone.tail.xz - space_origin

        local_tail_x = round(tail.dot(parent_x_axis), 3) * self.armature_export_scale
        local_tail_y = round(tail.dot(parent_y_axis), 3) * self.armature_export_scale

        local_head_x = round(head.dot(parent_x_axis), 3) * self.armature_export_scale
        local_head_y = round(head.dot(parent_y_axis), 3) * self.armature_export_scale

        local_tail_vec = Vector((local_tail_x, 0, local_tail_y))
        local_head_vec = Vector((local_head_x, 0, local_head_y))

        return {"head": local_head_vec.xz, "tail": local_tail_vec.xz}

    def get_bone_parent_mat(self, pbone):
        if pbone.parent == None:
            return [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        else:
            matrix_array = []
            for row in pbone.parent.matrix.row:
                for value in row:
                    matrix_array.append(round(value, 3))
            return matrix_array

    def bone_is_keyed_on_frame(self, bone, frame, animation_data, type="LOCATION"):  ### LOCATION, ROTATION, SCALE, ANY
        action = animation_data.action if animation_data != None else None
        type = "." + type.lower()
        if action != None:
            for fcurve in action.fcurves:
                if bone.name in fcurve.data_path and (type in fcurve.data_path or type == ".any"):
                    for keyframe in fcurve.keyframe_points:
                        if keyframe.co[0] == frame:
                            return True
        return False

    def create_animation_data(self, context):
        animation = OrderedDict()
        anim_collections = self.sprite_object.coa_tools.anim_collections

        # create default animation if no anim collection found
        if len(anim_collections) == 0:
            override = context.copy()
            override["active_object"] = self.sprite_object
            override["object"] = self.sprite_object
            bpy.ops.coa_tools.add_animation_collection(override)
            anim_collection = anim_collections[len(anim_collections)-1]
            anim_collection.name = "default"
            anim_collection.frame_end = 1

        # run through all animations
        for anim_index, anim in enumerate(anim_collections):
            if anim.name not in ["NO ACTION"]:
                if anim.name == "Restpose":
                    anim.frame_end = 0
                    if "default" in anim_collections:
                        continue
                anim_name = anim.name if anim.name != "Restpose" else "default"
                self.sprite_object.coa_tools.anim_collections_index = anim_index  ### set animation

                animation[anim_name] = OrderedDict()
                animation[anim_name]["bones"] = OrderedDict()
                animation[anim_name]["meshes"] = OrderedDict()
                animation[anim_name]["uv_swaps"] = OrderedDict()
                animation[anim_name]["mesh_opacities"] = OrderedDict()
                animation[anim_name]["coa_tools_events"] = OrderedDict()

                if anim_name in anim_collections:
                    for timeline_event in anim_collections[anim_name].timeline_events:
                        for event in timeline_event.event:
                            if str(timeline_event.frame) not in animation[anim_name]["coa_tools_events"]:
                                animation[anim_name]["coa_tools_events"][str(timeline_event.frame)] = []
                            animation[anim_name]["coa_tools_events"][str(timeline_event.frame)].append({"type": event.type, "key": event.value})


                for frame in range(anim.frame_end+1):

                    context.scene.frame_set(frame)

                    # bone relevant data
                    for pbone in self.armature.pose.bones:
                        start_pt = self.get_bone_head_tail(pbone, local=False)["head"]
                        end_pt = self.get_bone_head_tail(pbone, local=False)["tail"]

                        bake_animation = self.scene.coa_tools.export_bake_anim and frame%self.scene.coa_tools.export_bake_steps == 0
                        if str(frame) not in animation[anim_name]["bones"]:
                            animation[anim_name]["bones"][str(frame)] = OrderedDict()
                        animation[anim_name]["bones"][str(frame)][pbone.name] = {"start_pt": [round(start_pt.x, 3), round(start_pt.y, 3)],
                                                                                 "end_pt": [round(end_pt.x, 3), round(end_pt.y, 3)]}

                    # mesh relevant data
                    animation[anim_name]["meshes"][str(frame)] = OrderedDict()
                    animation[anim_name]["uv_swaps"][str(frame)] = OrderedDict()
                    animation[anim_name]["mesh_opacities"][str(frame)] = OrderedDict()
                    for sprite in self.sprite_data:
                        sprite_object = bpy.data.objects[sprite.name]

                        for i, slot in enumerate(sprite.slots):
                            slot_name = sprite.name + "_" + str(i).zfill(3) if sprite_object.coa_tools.type == "SLOT" else sprite.name
                            sprite.object.data = slot["slot"]
                            # collect shapekey animation
                            use_local_displacements = True if anim_name in self.mesh_deformed and slot_name in self.mesh_deformed[anim_name] else False
                            use_post_displacements = False
                            animation[anim_name]["meshes"][str(frame)][slot_name] = {"use_dq": True}
                            animation[anim_name]["meshes"][str(frame)][slot_name]["use_local_displacements"] = use_local_displacements
                            animation[anim_name]["meshes"][str(frame)][slot_name]["use_post_displacements"] = use_post_displacements
                            if use_local_displacements:
                                local_displacements = self.get_shapekey_vert_data(sprite.object, slot_name, sprite.object.data.vertices, anim, relative=True)
                                animation[anim_name]["meshes"][str(frame)][slot_name]["local_displacements"] = local_displacements
                            if use_post_displacements:
                                post_displacements = self.get_shapekey_vert_data(sprite.object, slot_name, sprite.object.data.vertices, anim, relative=True)
                                animation[anim_name]["meshes"][str(frame)][slot_name]["post_displacements"] = post_displacements

                            # collect slot swapping data
                            enabled = False if sprite_object.coa_tools.type == "MESH" else True
                            scale = [1, 1] if i == sprite_object.coa_tools.slot_index else [-1, -1]
                            animation[anim_name]["uv_swaps"][str(frame)][slot_name] = {"local_offset": [0, 0], "global_offset": [0, 0], "scale": scale, "enabled": enabled}

                            # collect mesh opacity and tint data
                            animation[anim_name]["mesh_opacities"][str(frame)][slot_name] = {"opacity": round(sprite_object.coa_tools.alpha*100, 1)}


                    self.export_progress_current += 1
                    current_progress = self.export_progress_current/max(1,self.export_progress_total)
                    context.window_manager.progress_update(current_progress)
        return animation

    def write_json_file(self):
        # get export, project and json path
        export_path = bpy.path.abspath(self.scene.coa_tools.export_path)
        json_path = os.path.join(export_path, self.project_name + "_data.json")
        zip_path = os.path.join(export_path, self.project_name + "_data.zip")

        # write json file
        if self.reduce_size:
            json_file = json.dumps(self.json_data, separators=(',', ':'))
        else:
            json_file = json.dumps(self.json_data, indent="  ", sort_keys=False)

        text_file = open(json_path, "w")
        text_file.write(json_file)
        text_file.close()

        zip_file = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write(json_path, os.path.basename(json_path))
        zip_file.close()

    def save_texture_atlas(self, context, img_atlas, img_path, atlas_name):
        context.scene.render.image_settings.color_mode = "RGBA"
        compression_rate = int(context.scene.render.image_settings.compression)
        context.scene.render.image_settings.compression = 85
        texture_path = os.path.join(img_path, atlas_name + "_atlas.png")
        img_atlas.save_render(texture_path)
        context.scene.render.image_settings.compression = compression_rate

    def setup_progress(self, context):
        self.export_progress_total = 0
        self.export_progress_current = 0
        for i, anim in enumerate(self.sprite_object.coa_tools.anim_collections):
            if anim.name not in ["Restpose", "NO ACTION"]:
                self.export_progress_total += anim.frame_end + 1
        context.window_manager.progress_begin(0, 100)
        context.window_manager.progress_update(0)


    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if not os.path.exists(self.export_path):
            self.report({"WARNING"}, "Please define a valid export path.")
            return{"FINISHED"}
        self.reduce_size = context.scene.coa_tools.minify_json
        bpy.ops.ed.undo_push(message="Start Export")
        bpy.ops.ed.undo_push(message="Start Export")
        self.json_data = self.setup_json_data()
        self.scene = context.scene

        scene = context.scene

        self.armature_export_scale = context.scene.coa_tools.armature_scale
        self.texture_export_scale = 1 / get_addon_prefs(context).sprite_import_export_scale
        self.sprite_scale = self.scene.coa_tools.sprite_scale

        # get sprite object, sprites and armature
        self.sprite_object = get_sprite_object(context.active_object)
        self.armature_orig = get_armature(self.sprite_object)

        # collect sprite data and armature for later usage
        self.sprite_data, self.armature = self.prepare_armature_and_sprites_for_export(context, scene)
        # do precalculations to check various things. makes the exporter overall faster
        self.bone_scaled = self.check_and_store_bone_scaling(context)
        self.bone_weights = self.store_bone_weights()
        self.mesh_deformed = self.check_mesh_deformation(context)

        self.sprite_object.coa_tools.anim_collections_index = 0
        self.setup_progress(context)
        for ob in context.scene.objects:
            ob.select_set(False)
        atlas_objects = self.create_dupli_atlas_objects(context)

        # generate and save atlas data
        self.armature.data.pose_position = "REST"
        width = self.scene.coa_tools.atlas_resolution_x if self.scene.coa_tools.atlas_mode == "LIMIT_SIZE" else 16384
        height = self.scene.coa_tools.atlas_resolution_y if self.scene.coa_tools.atlas_mode == "LIMIT_SIZE" else 16384
        img_atlas, merged_atlas_obj, atlas = TextureAtlasGenerator.generate_uv_layout(
            name="COA_UV_ATLAS",
            objects=atlas_objects,
            width=2,
            height=2,
            max_width=width,
            max_height=height,
            margin=self.scene.coa_tools.atlas_island_margin,
            texture_bleed=self.scene.coa_tools.export_texture_bleed,
            square=self.scene.coa_tools.export_square_atlas,
            output_scale=self.sprite_scale
        )
        self.armature.data.pose_position = "POSE"

        # collect all relevant json data for export
        points, uvs, indices = self.create_mesh_data(context, merged_atlas_obj)
        self.json_data["mesh"]["points"] = points
        self.json_data["mesh"]["uvs"] = uvs
        self.json_data["mesh"]["indices"] = indices
        self.json_data["mesh"]["regions"] = self.create_region_data(context, merged_atlas_obj)
        self.json_data["skeleton"] = self.create_skeleton_data()
        self.json_data["animation"] = self.create_animation_data(context)


        self.write_json_file()
        self.save_texture_atlas(context, img_atlas, self.export_path_abs, self.project_name)

        # cleanup scene and add an undo history step
        bpy.ops.ed.undo()
        bpy.ops.ed.undo_push(message="Export Creature")
        self.report({"INFO"}, "Export successful.")

        context.window_manager.progress_end()
        return {"FINISHED"}
