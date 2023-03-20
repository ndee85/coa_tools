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

class COATOOLS_OT_ExtractSlots(bpy.types.Operator):
    bl_idname = "coa_tools.extract_slots"
    bl_label = "Extract Slots"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.active_object
        active_collection = bpy.data.collections[context.scene.coa_tools.active_collection]
        if obj.type == "MESH" and len(obj.coa_tools.slot) > 0:
            for i, slot in enumerate(obj.coa_tools.slot):
                name = obj.name +"_"+ str(i).zfill(2)
                ob = obj.copy()
                functions.link_object(context, ob)
                ob.name = name
                ob.coa_tools.type = "MESH"
                ob.data = slot.mesh
                for slot in ob.coa_tools.slot:
                    ob.coa_tools.slot.remove(0)
                ob.parent = obj.parent
                ob.matrix_world = obj.matrix_world
                ob.select_set(True)
                context.view_layer.objects.active = ob
        
        active_collection.objects.unlink(obj)        
        bpy.data.objects.remove(obj)
        return {"FINISHED"}
        

class COATOOLS_OT_CreateSlotObject(bpy.types.Operator):
    bl_idname = "coa_tools.create_slot_object"
    bl_label = "Create Slot Object"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True
    
    slot_name: StringProperty(name="Slot Name")
    keep_sprite_position: BoolProperty(name="Keep Sprite Position",description="Keeps the sprite at current position by applying a new origin.",default=True)
    
    def draw(self,context):
        layout = self.layout
        if context.active_object.coa_tools.type == "MESH":
            layout.prop(self,"slot_name")
        layout.prop(self,"keep_sprite_position")
        
    
    def invoke(self,context,event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def objects_are_valid(self,context):
        count = 0
        for obj in context.selected_objects:
            if obj.type != "MESH":
                return False
            else:
                count += 1
        if count > 1:
            return True
        else:
            return False
                
    
    def execute(self, context):
        if not self.objects_are_valid(context):
            self.report({'INFO'},"Please select at least to Sprites to combine into a slot.")
            return{"CANCELLED"}
        
        active_collection = bpy.data.collections[context.scene.coa_tools.active_collection]
        
        name = str(context.active_object.name)
        init_obj = bpy.data.objects[context.active_object.name] 
        objs = context.selected_objects[:]
        obj = context.active_object.copy()
        functions.link_object(context, obj)
        context.view_layer.objects.active = obj
        if obj.coa_tools.type == "MESH":
            name = self.slot_name
            obj.name = self.slot_name
        
        
        if self.keep_sprite_position:
            for ob in objs:
                slots = []
                if ob.coa_tools.type == "MESH":
                    slots = [ob.data]
                elif ob.coa_tools.type == "SLOT":
                    for slot in ob.coa_tools.slot:
                        slots.append(slot.mesh)
                        
                ob.location[1] = obj.location[1]
                for i,slot in enumerate(slots):
                    ob_tmp = ob.copy()
                    functions.link_object(context, ob_tmp)
                    ob_tmp.data = slot
                    ob_tmp.select_set(True)
                    
                    ### deselect all objects, select the current from iteration
                    bpy.ops.object.select_all(action='DESELECT')
                    ob_tmp.select_set(True)
                    context.view_layer.objects.active = ob_tmp
                    
                    cursor_location = Vector(context.scene.cursor.location)
                    context.scene.cursor.location = obj.matrix_world.to_translation()
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                    context.scene.cursor.location = cursor_location
                    
                    active_collection.objects.unlink(ob_tmp)
                    bpy.data.objects.remove(ob_tmp)
        
        
            cursor_location = Vector(context.scene.cursor.location)
            context.scene.cursor.location = obj.matrix_world.to_translation()
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = cursor_location

        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        obj.coa_tools.type = "SLOT"
        for sprite in objs:
            if sprite != obj:
                if sprite.type == "MESH":
                    item = None
                    if sprite.coa_tools.type == "MESH":
                        if sprite.data.name not in obj.coa_tools.slot:
                            item = obj.coa_tools.slot.add()
                        else:
                            item = obj.coa_tools.slot[sprite.data.name]
                        item.mesh = sprite.data    
                        #item.name = sprite.data.name
                        item.index = len(obj.coa_tools.slot)-1
                        if sprite == init_obj:
                            obj.coa_tools.slot_index =  item.index
                            obj.coa_tools.slot_reset_index =  item.index
                    elif sprite.coa_tools.type == "SLOT" and sprite != init_obj:
                        for slot in sprite.coa_tools.slot:
                            item = obj.coa_tools.slot.add()
                            #item.name = slot.name
                            item.mesh = slot.mesh
                    if item != None:
                        item["active"] = False
        obj.coa_tools.slot[0].active = True
        ### delete original sprite
        for sprite in objs:
            active_collection.objects.unlink(sprite)
            bpy.data.objects.remove(sprite,do_unlink=True)
        for i,s in enumerate(obj.coa_tools.slot):
            s.index = i
        obj.name = name    
        return {"FINISHED"}
    

class COATOOLS_OT_MoveSlotItem(bpy.types.Operator):
    bl_idname = "coa_tools.move_slot_item"
    bl_label = "Move Slot Item"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    idx: IntProperty()
    ob_name: StringProperty()
    mode: StringProperty()
        
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = bpy.data.objects[self.ob_name]
        
        if self.mode == "UP":
            new_idx = max(self.idx-1,0)
            obj.coa_tools.slot.move(self.idx,new_idx)
        elif self.mode == "DOWN":
            new_idx = min(self.idx+1,len(obj.coa_tools.slot)-1)
            obj.coa_tools.slot.move(self.idx,new_idx)
        
        for i,s in enumerate(obj.coa_tools.slot):
            s.index = i
        
        return {"FINISHED"}
        
    
class COATOOLS_OT_RemoveFromSlot(bpy.types.Operator):
    bl_idname = "coa_tools.remove_from_slot"
    bl_label = "Remove From Slot"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    idx: IntProperty()
    ob_name: StringProperty()
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = bpy.data.objects[self.ob_name]
        active_collection = bpy.data.collections[context.scene.coa_tools.active_collection]
        slot = obj.coa_tools.slot[self.idx]
        active_idx = 0
        for i,s in enumerate(obj.coa_tools.slot):
            if s.active:
                active_idx = i
                break
        obj.coa_tools.slot.remove(self.idx)
        
        active_idx = max(0,(active_idx - 1))
        
        for i,s in enumerate(obj.coa_tools.slot):
            s["index"] = i    
        if len(obj.coa_tools.slot) > 0:
            obj.coa_tools.slot[active_idx].active = True
        else:
            active_collection.objects.unlink(obj)
            bpy.data.objects.remove(obj)    
        
#        for s in obj.coa_tools.slot:
#            if s.index > self.idx:
#                s["index"] -= 1
        return {"FINISHED"}
