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

######################################################################################################################################### Create Sprite Object
class COATOOLS_OT_CreateSpriteObject(bpy.types.Operator):
    bl_idname = "coa_tools.create_sprite_object"
    bl_label = "Create Sprite Object"
    bl_options = {"REGISTER","UNDO"}

    def execute(self, context):
        obj = context.active_object

        if context.active_object != None and obj.type == "ARMATURE" and obj.mode == "POSE":
            context.view_layer.objects.active = None
        bpy.ops.object.armature_add(radius=1,
                                    enter_editmode=False,
                                    align='WORLD',
                                    location=(0, 0, 0),
                                    rotation=(0, 0, 0))
        sprite_object = bpy.context.active_object
        sprite_object.name = "SpriteObject"
        sprite_object.show_name = True
        sprite_object.coa_tools["sprite_object"] = True
        sprite_object.show_axis = True
        bpy.ops.object.mode_set(mode="EDIT")
        for bone in sprite_object.data.edit_bones:
            sprite_object.data.edit_bones.remove(bone)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.ed.undo_push(message="Create Sprite Object")
        return{"FINISHED"}
