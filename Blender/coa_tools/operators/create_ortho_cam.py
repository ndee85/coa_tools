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
class COATOOLS_OT_CreateOrtpographicCamera(bpy.types.Operator):
    bl_idname = "coa_tools.create_ortho_cam"
    bl_label = "Camera Settings"
    bl_options = {"REGISTER","UNDO"}
    
    set_resolution: BoolProperty(name="Set Resolution", default = True)
    resolution: IntVectorProperty(name="Resolution", default=(960,600), size=2)
    create: BoolProperty(name="Create Camera",default=True)
    
    def draw(self, context):
        layout = self.layout
        if self.create:
            row = layout.row()
            row.prop(self,"set_resolution")
        
        row = layout.row()
        row.prop(self,"resolution")
    
    def invoke(self, context, event):
        wm = context.window_manager 
        return wm.invoke_props_dialog(self)
        
    def execute(self, context):
        sprite_object = None    
        if context.active_object != None:
            sprite_object = get_sprite_object(context.active_object)
        
        scene = context.scene
        if self.create:
            context.view_layer.objects.active = None
            bpy.ops.object.camera_add(enter_editmode=False, align='WORLD', location=(0, -self.resolution[0] * get_addon_prefs(context).sprite_import_export_scale, 0), rotation=(radians(90), 0, 0))
        cam = context.active_object
        context.view_layer.objects.active = cam
        cam.data.type = "ORTHO"
        scene.render.film_transparent = True
        
        if sprite_object != None:
            cam.parent = sprite_object
        
        if self.set_resolution:
            ortho_scale = max(self.resolution[0],self.resolution[1])
            cam.data.ortho_scale = ortho_scale/100
            
            scene.render.resolution_x = self.resolution[0]
            scene.render.resolution_y = self.resolution[1]
            cam.location[1] = -self.resolution[0] * get_addon_prefs(context).sprite_import_export_scale
            scene.render.resolution_percentage = 100
        scene.camera = cam
        if bpy.context.space_data.region_3d.view_perspective != "CAMERA":
            bpy.ops.view3d.view_camera()
        return{"FINISHED"}
    

class COATOOLS_OT_AlignCamera(bpy.types.Operator):
    bl_idname = "coa_tools.align_camera"
    bl_label = "Align 2D Camera"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    
    align: EnumProperty(name="Align Position",description="Align Position",items=(
                                ("BOTTOM_RIGHT","Bottom Right","Bottom Right"),
                                ("BOTTOM_CENTER","Bottom Center","Bottom Center"),
                                ("BOTTOM_LEFT","Bottom Left","Bottom Left"),
                                ("CENTER_RIGHT","Center Right","Center Right"),
                                ("CENTER_CENTER","Center Center","Center Center"),
                                ("CENTER_LEFT","Center Left","Center Left"),
                                ("TOP_RIGHT","Top Right","Top Right"),
                                ("TOP_CENTER","Top Center","Top Center"),
                                ("TOP_LEFT","Top Left","Top Left"),
                                ))
    
    x_multiplier = 1
    y_multiplier = 1
    offset_x = 0.0
    offset_y = 0.0
        
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self,context,event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self,context):
        layout = self.layout
        row = layout.row()

        row.prop(self, "align", text="Align Position")
    
    def execute(self, context):
        cam = context.active_object
        if cam.type == "CAMERA":
            if self.align == "TOP_LEFT":
                self.x_multiplier = -1
                self.y_multiplier = 1
                self.offset_x = 0.5
                self.offset_y = 0.5
            elif self.align == "TOP_CENTER":
                self.x_multiplier = -1
                self.y_multiplier = 1
                self.offset_x = 0.0
                self.offset_y = 0.5
            elif self.align == "TOP_RIGHT":
                self.x_multiplier = 1
                self.y_multiplier = 1
                self.offset_x = 0.5
                self.offset_y = 0.5
            elif self.align == "CENTER_LEFT":
                self.x_multiplier = -1
                self.y_multiplier = -1
                self.offset_x = 0.5
                self.offset_y = 0.0
            elif self.align == "CENTER_RIGHT":
                self.x_multiplier = 1
                self.y_multiplier = -1
                self.offset_x = 0.5
                self.offset_y = 0.0
            elif self.align == "CENTER_CENTER":
                self.x_multiplier = 0
                self.y_multiplier = 0
                self.offset_x = 0.0
                self.offset_y = 0.0
            elif self.align == "BOTTOM_LEFT":
                self.x_multiplier = -1
                self.y_multiplier = -1
                self.offset_x = 0.5
                self.offset_y = 0.5
            elif self.align == "BOTTOM_RIGHT":
                self.x_multiplier = 1
                self.y_multiplier = -1
                self.offset_x = 0.5
                self.offset_y = 0.5
            elif self.align == "BOTTOM_CENTER":
                self.x_multiplier = 1
                self.y_multiplier = -1
                self.offset_x = 0.0
                self.offset_y = 0.5
            
            cam.location[0] = self.x_multiplier * context.scene.render.resolution_x * get_addon_prefs(context).sprite_import_export_scale * self.offset_x
            #cam.location[1] = -self.x_multiplier * context.scene.render.resolution_x * get_addon_prefs(context).sprite_import_export_scale
            cam.location[2] = self.y_multiplier * context.scene.render.resolution_y * get_addon_prefs(context).sprite_import_export_scale * self.offset_y   
            
        return {"FINISHED"}

