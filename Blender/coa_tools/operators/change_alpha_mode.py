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
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, \
    EnumProperty, IntVectorProperty
import os
from bpy_extras.io_utils import ExportHelper, ImportHelper
import json
from bpy.app.handlers import persistent
from .. import functions


class COATOOLS_OT_ChangeAlphaMode(bpy.types.Operator):
    bl_idname = "coa_tools.change_alpha_mode"
    bl_label = "Change Alpha Mode"
    bl_description = ""
    bl_options = {"REGISTER"}

    items = (("BLEND","Blend","Blend"),("HASHED","Hashed","Hashed"),("CLIP","Clip","Clip"))
    blend_method: EnumProperty(name="Blend Method",items=items)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        sprite_object = functions.get_sprite_object(context.active_object)
        for sprite in sprite_object.children:
            if sprite.type == "MESH":
                for mat in sprite.data.materials:
                    mat.blend_method = self.blend_method
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class COATOOLS_OT_ChangeTextureInterpolationMode(bpy.types.Operator):
    bl_idname = "coa_tools.change_texture_interpolation_mode"
    bl_label = "Change Texture Interpolation Mode"
    bl_description = ""
    bl_options = {"REGISTER"}

    items = (("Linear","Linear","Linear"),("Closest","Closest","Closest"),("Cubic","Cubic","Cubic"),("Smart","Smart","Smart"))
    interpolation_method: EnumProperty(name="Interpolation Method", items=items)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        sprite_object = functions.get_sprite_object(context.active_object)
        for sprite in sprite_object.children:
            if sprite.type == "MESH":
                for mat in sprite.data.materials:
                    for node in mat.node_tree.nodes:
                        if node.type == "TEX_IMAGE":
                            node.interpolation = self.interpolation_method
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)