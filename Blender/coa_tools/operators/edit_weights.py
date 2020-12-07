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
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
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
from .. functions import *
from .. functions_draw import *
import traceback
import random

BONE_LAYERS = []
class COATOOLS_OT_EditWeights(bpy.types.Operator):
    bl_idname = "coa_tools.edit_weights"
    bl_label = "Select Child"
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def __init__(self):
        self.sprite_object_name = None
        self.obj_name = None
        self.armature_name = None
        self.active_object_name = None
        self.selected_object_names = []
        self.object_color_settings = {}
        self.use_unified_strength = False
        self.non_deform_bone_names = []
        self.deform_bone_names = []

    def armature_set_mode(self,context,mode,select):
        armature = bpy.data.objects[self.armature_name]
        armature.select_set(select)
        active_object_name = context.view_layer.objects.active.name
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode=mode)

        context.view_layer.objects.active = bpy.data.objects[active_object_name]

    def select_bone(self):
        armature = bpy.data.objects[self.armature_name]
        for bone in armature.data.bones:
            bone.select = False
        armature.data.bones.active = None

        for i,vertex_group in enumerate(bpy.data.objects[self.obj_name].vertex_groups):
            if vertex_group.name in armature.data.bones:
                bpy.data.objects[self.obj_name].vertex_groups.active_index = i
                bone = armature.data.bones[vertex_group.name]
                armature.data.bones.active = bone
                break

    def exit_edit_weights(self, context):
        tool_settings = context.scene.tool_settings
        tool_settings.unified_paint_settings.use_unified_strength = self.use_unified_strength
        set_local_view(False)
        obj = bpy.data.objects[self.obj_name]
        obj.hide_viewport = False
        obj.select_set(True)
        context.view_layer.objects.active = obj
        armature = get_armature(get_sprite_object(obj))
        armature.hide_viewport = False
        bpy.ops.object.mode_set(mode="OBJECT")
        for i,bone_layer in enumerate(BONE_LAYERS):
            armature.data.layers[i] = bone_layer

        for name in self.selected_object_names:
            obj = bpy.data.objects[name]
            obj.select_set(True)
        context.view_layer.objects.active = bpy.data.objects[self.active_object_name]
        self.unhide_non_deform_bones(context)

    def exit_edit_mode(self, context):
        ### remove draw call
        if self.draw_handler != None:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
            self.draw_handler = None

        sprite_object = bpy.data.objects[self.sprite_object_name]
        
        self.exit_edit_weights(context)
        sprite_object.coa_tools.edit_weights = False
        sprite_object.coa_tools.edit_mode = "OBJECT"
        bpy.context.space_data.shading.type = "SOLID"
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces[0].overlay.show_paint_wire = False

        # bpy.ops.ed.undo_push(message="Exit Edit Weights")
        return {"FINISHED"}

    def modal(self, context, event):
        try:
            if get_local_view(context) == None or (context.active_object != None and context.active_object.mode != "WEIGHT_PAINT") or context.active_object == None:
                return self.exit_edit_mode(context)
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"},"An Error occured, please check console for more Information.")
            self.exit_edit_mode(context)

        return {"PASS_THROUGH"}

    def unhide_deform_bones(self,context):
        self.deform_bone_names = []
        armature = bpy.data.objects[self.armature_name]
        for bone in armature.data.bones:
            if bone.hide and bone.use_deform:
                self.deform_bone_names.append(bone.name)
                bone.hide = False

    def hide_deform_bones(self,context):
        armature = bpy.data.objects[self.armature_name]
        for bone_name in self.deform_bone_names:
            bone = armature.data.bones[bone_name]
            bone.hide = True

    def hide_non_deform_bones(self,context):
        self.non_deform_bone_names = []
        armature = bpy.data.objects[self.armature_name]
        for bone in armature.data.bones:
            if not bone.hide and not bone.use_deform:
                self.non_deform_bone_names.append(bone.name)
                bone.hide = True

    def unhide_non_deform_bones(self,context):
        armature = bpy.data.objects[self.armature_name]
        for bone_name in self.non_deform_bone_names:
            bone = armature.data.bones[bone_name]
            bone.hide = False


    def create_armature_modifier(self,context,obj,armature):
        for mod in obj.modifiers:
            if mod.type == "ARMATURE":
                return mod
        mod = obj.modifiers.new("Armature","ARMATURE")
        mod.object = armature
        return mod

    def invoke(self, context, event):
        if context.active_object == None or context.active_object.type != "MESH":
            self.report({"ERROR"},"Sprite is not selected. Cannot go in Edit Mode.")
            return{"CANCELLED"}
        obj = bpy.data.objects[context.active_object.name]
        self.obj_name = context.active_object.name
        self.sprite_object_name = get_sprite_object(context.active_object).name
        sprite_object = bpy.data.objects[self.sprite_object_name]
        if get_armature(sprite_object) == None or get_armature(sprite_object) not in context.visible_objects:
            self.report({'WARNING'},'No Armature Available or Visible')
            return{"CANCELLED"}
        self.armature_name = get_armature(sprite_object).name
        armature = bpy.data.objects[self.armature_name]


        self.create_armature_modifier(context,obj,armature)

        scene = context.scene
        tool_settings = scene.tool_settings
        self.use_unified_strength = tool_settings.unified_paint_settings.use_unified_strength
        tool_settings.unified_paint_settings.use_unified_strength = True

        context.window_manager.modal_handler_add(self)

        self.active_object_name = context.active_object.name
        
        for obj in context.selected_objects:
            self.selected_object_names.append(obj.name)
        
        sprite_object.coa_tools.edit_weights = True
        sprite_object.coa_tools.edit_mode = "WEIGHTS"
        
        
        self.hide_non_deform_bones(context)
        self.unhide_deform_bones(context)
            
        if armature != None:
            self.armature_set_mode(context,"POSE",True)
            global BONE_LAYERS
            BONE_LAYERS = []
            for i,bone_layer in enumerate(armature.data.layers):
                BONE_LAYERS.append(bool(bone_layer))
                armature.data.layers[i] = True
            self.select_bone()
            
        sprite = context.active_object
        if sprite.parent != get_armature(sprite_object):
            create_armature_parent(context)

        set_local_view(True)
        
        context.scene.tool_settings.use_auto_normalize = True
        
        ### zoom to selected mesh/sprite
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        obj = bpy.data.objects[self.obj_name]    
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.view3d.view_selected()

        ### set correct viewport shading
        # bpy.context.space_data.shading.type = 'RENDERED'
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces[0].overlay.show_paint_wire = True
        
        ### enter weights mode
        bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
        
        
        ### start draw call
        # args = ()
        # self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, "WINDOW", "POST_PIXEL")
        args = ()
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, "WINDOW", "POST_PIXEL")
        return {"RUNNING_MODAL"}


    def coord_3d_to_2d(self, coord):
        region = bpy.context.region
        rv3d = bpy.context.space_data.region_3d
        coord_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(region, rv3d, coord)
        return coord_2d

    def draw_coords(self, coords=[], color=[], indices=[], draw_type="LINE_STRIP", shader_type="2D_UNIFORM_COLOR", line_width=2, point_size=None):  # draw_types -> LINE_STRIP, LINES, POINTS
        bgl.glLineWidth(line_width)
        if point_size != None:
            bgl.glPointSize(point_size)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)

        shader = gpu.shader.from_builtin(shader_type)
        if len(indices) > 0:
            batch = batch_for_shader(shader, draw_type, {"pos": coords}, indices=indices)
        else:
            batch = batch_for_shader(shader, draw_type, {"pos": coords})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

        bgl.glDisable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_LINE_SMOOTH)
        return shader

    def draw_callback_px(self):
        obj = bpy.context.active_object

        if obj != None:
            me = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
            v_group = obj.vertex_groups.active

            for i, vert in enumerate(me.vertices):
                if not vert.hide:
                    weight = 0.0
                    for group in vert.groups:
                        if v_group != None:
                            if group.group == v_group.index:
                                weight = group.weight
                    alpha = 0.0 if weight == 0.0 else 1.0

                    vert_ob_space = obj.matrix_world @ vert.co
                    vert_2d = self.coord_3d_to_2d(vert_ob_space)

                    colorband = [
                        Vector([1.0, 0.0, 0.0]),
                        Vector([1.000000, 0.119172, 0.000000]),
                        Vector([1.000000, 0.625478, 0.000000]),
                        Vector([0.0, 1.0, 0.0]),
                        Vector([0.000000, 1.000000, 0.738375]),
                        Vector([0.0, 0.0, 1.0]),
                    ]
                    colorband.reverse()
                    color_index = int((len(colorband)-1)*weight)
                    segment_length = 1.0/(len(colorband)-1)
                    segment_weight = (weight - segment_length*color_index) / segment_length
                    if weight < 1.0:
                        final_color = colorband[color_index].lerp(colorband[color_index+1], segment_weight)
                    else:
                        final_color = colorband[len(colorband)-1]
                    color = [final_color[0], final_color[1], final_color[2], alpha]

                    detail = 9
                    radius = 6
                    segment = (2 * math.pi) / detail
                    coords = []
                    indices = []
                    coords.append(vert_2d)

                    for i in range(detail + 1):
                        x = vert_2d.x + radius * math.cos(segment * i)
                        y = vert_2d.y + radius * math.sin(segment * i)

                        coords.append(Vector((x,y)))
                        if i <= detail:
                            indices.append([0,i,i+1])
                    self.draw_coords(coords=coords, indices=indices, color=color, draw_type=CONSTANTS.DRAW_TRIS)

                    # self.draw_coords(coords=[vert_2d], color=color, draw_type=CONSTANTS.DRAW_POINTS, point_size=8)
