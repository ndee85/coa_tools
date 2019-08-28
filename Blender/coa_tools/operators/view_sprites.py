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
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty

from .. import outliner
from .. functions import *

class COATOOLS_OT_ChangeZOrdering(bpy.types.Operator):
    bl_idname = "coa_tools.change_z_ordering"
    bl_label = "Change Zordering"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    active_sprite: StringProperty()
    all_sprites_string: StringProperty()
    index: IntProperty()
    direction: StringProperty() ## UP - DOWN

    def __init__(self):
        self.sprites = eval(self.all_sprites_string)

    @classmethod
    def poll(cls, context):
        return True

    def get_sprite_index(self, active_sprite_name):
        for i, name in enumerate(self.sprites):
            if name == active_sprite_name:
                return i
        return -1

    def execute(self, context):
        active_object = bpy.data.objects[context.active_object.name] if context.active_object != None else None
        active_sprite_name = context.scene.coa_tools.outliner[self.index].display_name

        active_sprite_index = self.get_sprite_index(active_sprite_name)
        lower_sprite_index = (active_sprite_index-1) % len(self.sprites)
        higher_sprite_index = (active_sprite_index+1) % len(self.sprites)

        active_sprite = bpy.data.objects[active_sprite_name]

        sorted_sprites = self.sprites[:]
        if self.direction == "DOWN":
            sorted_sprites.insert(lower_sprite_index, sorted_sprites.pop(active_sprite_index))
        elif self.direction == "UP":
            sorted_sprites.insert(higher_sprite_index, sorted_sprites.pop(active_sprite_index))
        for i, sprite_name in enumerate(sorted_sprites):
            sprite = bpy.data.objects[sprite_name]
            sprite.coa_tools.z_value = len(sorted_sprites) - i - 1

        context.view_layer.objects.active = active_sprite
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.object.mode_set(mode="OBJECT")
        context.view_layer.objects.active = active_object
        return {"FINISHED"}
        

class COATOOLS_OT_ViewSprite(bpy.types.Operator):
    bl_idname = "coa_tools.view_sprite"
    bl_label = "View Sprite"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    type: StringProperty(default="VIEW_SELECTED")
    name: StringProperty(default="")
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        
        active_object = bpy.data.objects[context.active_object.name]
        active_object_mode = active_object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        sprite_object = get_sprite_object(context.scene.objects[self.name])
        children = get_children(context, sprite_object, ob_list=[])
        selected_objects = []
        
        
        if self.type == "VIEW_ALL":
            for obj in context.selected_objects:
                selected_objects.append(obj)
                
                
            for obj in context.scene.objects:
                obj.select_set(False)
                
            context.view_layer.objects.active = context.scene.objects[self.name]
            context.scene.objects[self.name].select_set(True)
            
            for obj in children:    
                obj.select_set(True)
            bpy.ops.view3d.view_selected()
            
            for obj in context.selected_objects:
                if obj not in selected_objects:
                    obj.select_set(False)
            context.view_layer.objects.active = active_object
            active_object.select_set(True)

            for area in context.screen.areas:
                if area.type == "VIEW_3D":
                    area.spaces[0].region_3d.view_distance = area.width * 0.007
            
        bpy.ops.object.mode_set(mode=active_object_mode)
        return {"FINISHED"}
