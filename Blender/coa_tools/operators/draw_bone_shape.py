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
from .. functions import *


def get_bone_shapes(self, context):
    enum_items = []
    names_list = []
    i = 0
    
    for obj in bpy.data.objects:
        if "_custom_shape" in obj.name:
            names_list.append(obj.name)
    names_list = sorted(names_list)        
    
    for name in names_list:
        enum_items.append((name,name,name,"MESH_DATA",i))
        i += 1
    enum_items.append(("NEW_SHAPE","New Shape","Create new Shape","FILE_NEW",i+1))        
    return enum_items        


class COATOOLS_OT_DrawBoneShape(bpy.types.Operator):
    bl_idname = "coa_tools.draw_bone_shape"
    bl_label = "Create Bone Shape"
    
    bone_shapes: EnumProperty(name="Bone Shapes",description="List of all custom Bone Shapes.",items=get_bone_shapes)
    
    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.prop(self,"bone_shapes")
    
    def invoke(self,context,event):
        
        
        self.bone_shapes = "NEW_SHAPE"
        if context.active_pose_bone != None:
            shape_name = context.active_pose_bone.name + "_custom_shape"
            if context.active_object.type == "ARMATURE" and (context.active_pose_bone.custom_shape != None or shape_name in bpy.data.objects):
                shape_name = context.active_pose_bone.custom_shape.name if context.active_pose_bone.custom_shape != None else context.active_pose_bone.name + "_custom_shape"
                self.bone_shapes = shape_name
        
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            self.report({'WARNING'}, "Select Bone in Pose Mode.")
        return {'FINISHED'}

    def execute(self, context):
        if context.active_object.type == "ARMATURE" and context.active_object.mode == "POSE":
            if self.bone_shapes == "NEW_SHAPE":
                bpy.ops.coa_tools.edit_mesh(mode="DRAW_BONE_SHAPE")
            else:
                shape_name = context.active_pose_bone.name + "_custom_shape"
                if shape_name not in bpy.data.objects:
                    bone_shape = bpy.data.meshes.new_from_object(bpy.data.objects[self.bone_shapes],preserve_all_data_layers=False, depsgraph=None)
                    bone_shape.name = shape_name
                bpy.ops.coa_tools.edit_mesh(mode="DRAW_BONE_SHAPE", new_shape_name=self.bone_shapes)
        else:
            self.report({'WARNING'}, "Select Bone in Pose Mode.")
        return {'FINISHED'}

