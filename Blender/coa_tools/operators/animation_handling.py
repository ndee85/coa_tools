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

class COATOOLS_OT_AddKeyframe(bpy.types.Operator):
    bl_idname = "coa_tools.add_keyframe"
    bl_label = "Add Keyframe"
    bl_description = "Add Keyframe"
    bl_options = {"REGISTER"}
    
    prop_name: StringProperty()
    add_keyframe: BoolProperty(default=True)
    interpolation: EnumProperty(default="BEZIER",items=(("BEZIER","BEZIER","BEZIER","IPO_BEZIER",0),("LINEAR","LINEAR","LINEAR","IPO_LINEAR",1),("CONSTANT","CONSTANT","CONSTANT","IPO_CONSTANT",2)))
    default_interpolation: StringProperty()
    obj: StringProperty(default="")
    key_obj = None
    @classmethod
    def poll(cls, context):
        return True

    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.prop(self,"interpolation",expand=True)
    
    def set_fcurve_interpolation(self,context,sprite,data_path):
        for fcurve in sprite.animation_data.action.fcurves:
            if data_path in fcurve.data_path:
                for key in fcurve.keyframe_points:
                    if key.co[0] == context.scene.frame_current:
                        key.interpolation = self.interpolation
    
    def create_keyframe(self,context,event,data_path,group=""):
        sprite = context.active_object
        sprite_object = get_sprite_object(sprite)
        
        sprites = context.selected_objects if self.key_obj == None else [self.key_obj]
        if sprite_object.coa_tools.anim_collections_index > 1:
            if self.add_keyframe:
                #for sprite in context.selected_objects:
                for sprite in sprites:    
                    if sprite.animation_data != None and sprite.animation_data.action != None:
                        if group != "":
                            sprite.keyframe_insert(data_path,group=group)
                        else:
                            sprite.keyframe_insert(data_path)    
                        self.set_fcurve_interpolation(context,sprite,data_path)
                    else:
                        create_action(context,obj=sprite)
                        if group != "":
                            sprite.keyframe_insert(data_path,group=group)
                        else:
                            sprite.keyframe_insert(data_path)   
                        self.set_fcurve_interpolation(context,sprite,data_path)
                            
                self.report({'INFO'},str("Keyframe added at frame "+str(context.scene.frame_current)+"."))    
            else:
                for sprite in sprites:#context.selected_objects:
                    if sprite.animation_data != None and sprite.animation_data.action != None:
                        sprite.keyframe_delete(data_path)
                        
                        collection = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
                        action_name = collection.name + "_" +sprite.name
                        if action_name in bpy.data.actions:
                            action = bpy.data.actions[action_name]
                            if len(action.fcurves) == 0:
                                action.use_fake_user = False
                                action.user_clear()
                        self.report({'INFO'},str("Keyframe deleted at frame "+str(context.scene.frame_current)+"."))
                        set_action(context)
                    else:
                        self.report({'WARNING'},str("Sprite has no Animation assigned."))
        else:
            self.report({'WARNING'},str("No Animation selected"))
    
    
    def create_bone_keyframe(self,context,event,prop_name):
        obj = context.active_object if self.key_obj == None else self.key_obj
        if obj != None and obj.type == "ARMATURE" and obj.mode == "POSE":
            for pose_bone in context.selected_pose_bones:
                data_path = 'pose.bones["'+str(pose_bone.name)+'"].'+prop_name
                
                if pose_bone.rotation_mode == "QUATERNION" and prop_name == "rotation":
                    data_path = data_path.replace(".rotation",".rotation_quaternion")
                else:
                    data_path = data_path.replace(".rotation",".rotation_euler")
                    
                self.create_keyframe(context,event,data_path,group=pose_bone.name)
                
    
    def invoke(self,context,event):
        wm = context.window_manager
        if event.ctrl and self.add_keyframe:
            
            return wm.invoke_props_dialog(self)
        else:
            try:
                self.interpolation = self.default_interpolation
            except:
                pass    
            self.execute(context)
            self.obj = ""
            self.key_obj = None
            return {'FINISHED'}
            
        
    def execute(self,context):
        
        if self.obj != "":
            self.key_obj = bpy.data.objects[self.obj]
            
        event = None
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        
        if len(sprite_object.coa_tools.anim_collections) > 0:
            anim = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
            if self.prop_name in ["location","rotation","scale","LocRotScale"]:
                if self.prop_name == "LocRotScale":
                    data_path = "location"
                    self.create_bone_keyframe(context,event,data_path)
                    
                    data_path = "rotation"
                    self.create_bone_keyframe(context,event,data_path)
                    
                    data_path = "scale"
                    self.create_bone_keyframe(context,event,data_path)
                else:
                    self.create_bone_keyframe(context,event,self.prop_name)
            else:
                self.create_keyframe(context,event,self.prop_name)
        else:
            self.report({'WARNING'},"First create an animation collection.")        
        self.obj = ""
        self.key_obj = None    
        return {"FINISHED"}   

class COATOOLS_OT_DuplicateAnimationCollection(bpy.types.Operator):
    bl_idname = "coa_tools.duplicate_animation_collection"
    bl_label = "Duplicate Animation Collection"
    bl_description = "Duplicate Animation Collection"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    sprite_object = None
    
    def execute(self, context):
        self.sprite_object = get_sprite_object(context.active_object)
        
        if self.sprite_object != None:
            
            name_array = []
            for item in self.sprite_object.coa_tools.anim_collections:
                name_array.append(item.name)
            
            active_anim_collection = self.sprite_object.coa_tools.anim_collections[self.sprite_object.coa_tools.anim_collections_index]
            active_anim_name = str(active_anim_collection.name)
            active_anim_frame_end = active_anim_collection.frame_end
            active_anim_frame_action_collection = active_anim_collection.action_collection
            
            new_anim_collection = self.sprite_object.coa_tools.anim_collections.add()
            
            new_anim_collection_name = check_name(name_array,active_anim_name)
            new_anim_collection.name = new_anim_collection_name
            new_anim_collection.frame_end = active_anim_frame_end
            new_anim_collection.action_collection = active_anim_frame_action_collection
            
            for action in bpy.data.actions:
                name = active_anim_name + "_"
                if name in action.name:
                    
                    copied_action = action.copy()
                    new_name = new_anim_collection_name + "_"
                    new_name = str(action.name).replace(name,new_name)
                    copied_action.name = new_name
            self.sprite_object.coa_tools.anim_collections_index = len(self.sprite_object.coa_tools.anim_collections)-1
            
        return {"FINISHED"}
        


class COATOOLS_OT_AddAnimationCollection(bpy.types.Operator):
    bl_idname = "coa_tools.add_animation_collection"
    bl_label = "Add Animation Collection"
    bl_description = "Add new Animation Collection"
    bl_options = {"REGISTER"}

    def get_actions(self, context):
        ACTIONS = []
        i = -1

        sprite_object = get_sprite_object(context.active_object)
        already_used_actions = []
        for anim in sprite_object.coa_tools.anim_collections:
            for action in bpy.data.actions:
                if anim.name in action.name:
                    already_used_actions.append(action)

        for action in bpy.data.actions:
            if action not in already_used_actions:
                i += 1
                ACTIONS.append((action.name, action.name, action.name, "ACTION", i))
        return ACTIONS

    sprite_object = None
    armature = None
    type: EnumProperty(items=(("NEW","New","New"), ("EXISTING","Existing","Existing")))
    action: EnumProperty(name="Action",items=get_actions)
    animation_name: StringProperty(name="Name", default="NewCollection")

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "type", expand=True)
        if self.type == "EXISTING":
            row = layout.row()
            row.prop(self, "action", text="Animation")
        else:
            row = layout.row()
            row.prop(self, "animation_name")
    
    def create_actions_collection(self, context, action_name):
        if self.sprite_object != None:
            if len(self.sprite_object.coa_tools.anim_collections) == 0:
                item = self.sprite_object.coa_tools.anim_collections.add()
                item.name = "NO ACTION"
                
                item = self.sprite_object.coa_tools.anim_collections.add()
                item.name = "Restpose"
                item.frame_start = 0
                item.frame_end = 1

            item = self.sprite_object.coa_tools.anim_collections.add()
            if self.type == "NEW":
                item.name = check_name(self.sprite_object.coa_tools.anim_collections,self.animation_name)
            elif self.type == "EXISTING":
                name = action_name
                if self.armature.name in name:
                    name = action_name.split("_" + self.armature.name)[0]
                item.name = name
            item.name_old = item.name
            item.action_collection = True
            
            self.sprite_object.coa_tools.anim_collections_index = len(self.sprite_object.coa_tools.anim_collections)-1
            return item

    
    def create_actions(self,context):
        item = self.sprite_object.coa_tools.anim_collections[self.sprite_object.coa_tools.anim_collections_index]

        children = get_children(context,self.sprite_object,ob_list=[])
        anim_objects = []
        if self.sprite_object.type == "ARMATURE":
            anim_objects.append(self.sprite_object)
        for child in children:
            anim_objects.append(child)

        for child in anim_objects:
            if child.type == "ARMATURE":
                action_name = item.name + "_" + child.name
                
                action = None
                if action_name not in bpy.data.actions:
                    action = bpy.data.actions.new(action_name)
                else:
                    action = bpy.data.actions[action_name]
                action.use_fake_user = True    
                if child.animation_data == None:
                    child.animation_data_create()
                child.animation_data.action = action

    def rename_actions(self, action_name):
        for action in bpy.data.actions:
            if action.name == action_name:
                action.name = action_name + "_" + self.armature.name
        self.sprite_object.coa_tools.anim_collections_index = len(self.sprite_object.coa_tools.anim_collections)-1

    def invoke(self, context, event):
        self.sprite_object = get_sprite_object(context.active_object)
        self.armature = get_armature(self.sprite_object)
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        self.sprite_object = get_sprite_object(context.active_object)
        self.armature = get_armature(self.sprite_object)

        if self.type == "NEW":
            self.create_actions_collection(context, self.animation_name)
            self.create_actions(context)
        elif self.type == "EXISTING":
            collection = self.create_actions_collection(context, self.action)
            self.rename_actions(collection.name)
        return {"FINISHED"}
        
class COATOOLS_OT_RemoveAnimationCollection(bpy.types.Operator):
    bl_idname = "coa_tools.remove_animation_collection"
    bl_label = "Remove Animation Collection"
    bl_description = "Delete selected Animation Collection"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True
    
    sprite_object = None
    
    def remove_actions_collection(self,context):
        if self.sprite_object != None:
            if self.sprite_object.coa_tools.anim_collections[self.sprite_object.coa_tools.anim_collections_index].name != "NO ACTION" and self.sprite_object.coa_tools.anim_collections[self.sprite_object.coa_tools.anim_collections_index].name != "Restpose":
                self.sprite_object.coa_tools.anim_collections.remove(self.sprite_object.coa_tools.anim_collections_index)
            if self.sprite_object.coa_tools.anim_collections_index > 2:
                self.sprite_object.coa_tools.anim_collections_index = self.sprite_object.coa_tools.anim_collections_index - 1
            
            if len(self.sprite_object.coa_tools.anim_collections) < 3:
                self.sprite_object.coa_tools.anim_collections.remove(0)
                self.sprite_object.coa_tools.anim_collections.remove(0)
            
    def remove_actions(self,context):
        item = self.sprite_object.coa_tools.anim_collections[self.sprite_object.coa_tools.anim_collections_index]
        
        for child in get_children(context,self.sprite_object,ob_list=[]):
            action_name = item.name + "_" + child.name
            
            if action_name in bpy.data.actions:
                if child.animation_data != None and child.animation_data.action == bpy.data.actions[action_name]:
                    child.animation_data_clear()
                bpy.data.actions[action_name].use_fake_user = False
                bpy.data.actions[action_name].user_clear()    
                bpy.data.actions.remove(bpy.data.actions[action_name])
        for area in context.screen.areas:
            if area.type == "DOPESHEETH_EDITOR":
                area.tag_redraw()
        context.view_layer.update()
            
                    
    def execute(self, context):
        self.sprite_object = get_sprite_object(context.active_object)
        if len(self.sprite_object.coa_tools.anim_collections) > 0:
            
            self.remove_actions(context)
            self.remove_actions_collection(context)
            
        return {"FINISHED"}
                
class COATOOLS_OT_CreateNlaTrack(bpy.types.Operator):
    bl_idname = "coa_operator.create_nla_track"
    bl_label = "Create NLA Track"
    bl_description = "Generate NLA Strips."
    bl_options = {"REGISTER","UNDO"}
    
    
    start: IntProperty(default=0)
    repeat: IntProperty(default=1)
    scale: FloatProperty(default=1.0)
    insert_at_cursor: BoolProperty(default=True)
    anim_collection_name: StringProperty()
    auto_blend: BoolProperty(default=True)
    extrapolation: EnumProperty(default="NOTHING",items=(("HOLD_FORWARD","Hold Forward","HOLD_FORWARD"),("HOLD","Hold","HOLD"),("NOTHING","Nothing","NOTHING")) )

    def check(self,context):
        return True
    
    @classmethod
    def poll(cls, context):
        return True

    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.prop(self,"insert_at_cursor",text="Insert Strip at Cursor Location")
        row = layout.row()
        row.prop(self,"auto_blend",text="Auto Blending")
        row = layout.row()
        if self.insert_at_cursor:
            row.active = False
            row.enabled = False
        row.prop(self,"start",text="Insert at Frame")
        row = layout.row()
        row.prop(self,"repeat",text="Repeat Strip")
        row = layout.row()
        row.prop(self,"scale",text="Scale Strip")
        row = layout.row()
        row.prop(self,"extrapolation",text="Strip Extrapolation")
        

    def invoke(self,context,event):
        wm = context.window_manager
        self.start = 0
        self.repeat = 1
        self.scale = 1.0
        #self.insert_at_cursor = True
        return wm.invoke_props_dialog(self)
    
    def get_empty_track(self,anim_data,strip_range):
        if len(anim_data.nla_tracks) == 0:
            return anim_data.nla_tracks.new()
        
        strip_space = range(strip_range[0],strip_range[1]+1)
        
        intersecting_strip_found = False
        for i,track in enumerate(anim_data.nla_tracks):
            track = anim_data.nla_tracks[i]
            if len(track.strips) == 0:
                return track
            
            for strip in track.strips:
                if (strip_range[0] > strip.frame_start and strip_range[0] < strip.frame_end) or (strip_range[1] > strip.frame_start and strip_range[1] < strip.frame_end) or (strip_range[0] == strip.frame_start and strip_range[1] == strip.frame_end):
                    intersecting_strip_found = True

        if not intersecting_strip_found:
            return track


        return anim_data.nla_tracks.new()

    def execute(self, context):
        obj = bpy.context.active_object
        sprite_object = get_sprite_object(obj)
        children = get_children(context,sprite_object,ob_list=[])

        context.scene.coa_tools.nla_mode = "NLA"

        if self.anim_collection_name == "":
            anim_collection = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
        else:
            anim_collection = sprite_object.coa_tools.anim_collections[self.anim_collection_name]

        if self.insert_at_cursor:
            self.start = context.scene.frame_current

        for child in children:
            if child.animation_data != None:
                for track in child.animation_data.nla_tracks:
                    for strip in track.strips:
                        strip.select = False

                action_name = anim_collection.name + "_" + child.name
                if action_name in bpy.data.actions:
                    action_start = 0
                    action_end = anim_collection.frame_end
                    strip_start = self.start
                    strip_end = self.start + anim_collection.frame_end


                    action = bpy.data.actions[action_name]

                    if child.animation_data != None:
                        child.animation_data_create()
                        anim_data = child.animation_data
                        nla_track = self.get_empty_track(anim_data,[strip_start,strip_end])

                        strip = nla_track.strips.new(action_name,self.start,action)
                        strip.action_frame_start = action_start
                        strip.action_frame_end = action_end
                        
                        strip.frame_start = strip_start
                        strip.frame_end = strip_end
                        strip.repeat = self.repeat
                        strip.use_auto_blend = self.auto_blend
                        strip.scale = self.scale
                        strip.extrapolation = self.extrapolation
                    
                    
        return {"FINISHED"}
    
class COATOOLS_OT_BatchRender(bpy.types.Operator):
#class BatchRender(bpy.types.RenderEngine):
    bl_idname = "coa_tools.batch_render"
    bl_label = "Batch Render"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True
    
    def cam_found(self,context):
        for obj in context.scene.objects:
            if obj.type == "CAMERA":
                return True
        return False    
    
    def invoke(self, context, event):
        if not self.cam_found(context):
            self.report({'WARNING'},"No Camera in scene found.")
            return {'FINISHED'}
        
        wm = context.window_manager
        ### open render path
        path = context.scene.render.filepath.replace("\\","/")
        dirpath = path[:path.rfind("/")]
        dirpath = dirpath.replace("//","")
        basename = os.path.basename(bpy.data.filepath)
        blend_path = bpy.data.filepath.partition(basename)[0]
        output = os.path.join(blend_path,dirpath)
        
        if not os.path.isdir(output):
            os.makedirs(output)
        bpy.ops.wm.path_open(filepath = output)    
        
        scene = context.scene
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        if sprite_object != None:
            
            idx = int(sprite_object.coa_tools.anim_collections_index)
            
            for i in range(len(sprite_object.coa_tools.anim_collections)):
                
                anim_name = sprite_object.coa_tools.anim_collections[i].name
                if anim_name not in ["NO ACTION","Restpose"]:
                    sprite_object.coa_tools.anim_collections_index = i
                    set_action(context,item= sprite_object.coa_tools.anim_collections[i])
                    bpy.context.scene.frame_start = 0
                    bpy.context.scene.frame_end = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index].frame_end
                    
                    path = context.scene.render.filepath.replace("\\","/")
                    dirpath = path[:path.rfind("/")]
                    final_path = dirpath + "/" + anim_name + "_"
                    context.scene.render.filepath = final_path
                    
                    bpy.ops.render.render("EXEC_DEFAULT",animation=True,write_still=False,use_viewport=True,scene=context.scene.name)
                    #bpy.ops.render.render("INVOKE_DEFAULT",animation=True,write_still=False,use_viewport=True,scene=context.scene.name)
        
            sprite_object.coa_tools.anim_collections_index = idx
        return {"FINISHED"}


### Add Timeline Event -> Dragonbones
class COATOOLS_OT_AddEvent(bpy.types.Operator):
    bl_idname = "coa_tools.add_event"
    bl_label = "Add Event"
    bl_description = ""
    bl_options = {"REGISTER"}

    index: IntProperty()
    type: EnumProperty(
        name="Object Type",
        default="SOUND",
        items=(
            ("SOUND", "Sound", "Sound", "SOUND", 0),
            ("EVENT", "Event", "Event", "PHYSICS", 1),
            ("ANIMATION", "Animation", "Animation", "ACTION", 2)
        )
    )

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "type", text="Event Type")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        sprite_object = get_sprite_object(obj)

        anim = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]

        timeline_events = anim.timeline_events[self.index]
        if context.scene.coa_tools.runtime_format == "DRAGONBONES":
            for item in timeline_events.event:
                if item.type in ["SOUND", "ANIMATION"] and item.type == self.type:
                    message = "Only one " + self.type + " Event allowed."
                    self.report({"WARNING"}, message)
                    return {"FINISHED"}

        item = timeline_events.event.add()

        if context.scene.coa_tools.runtime_format == "DRAGONBONES":
            if self.type == "SOUND":
                item.value = "soundEvent"
            elif self.type == "EVENT":
                item.value = "eventName"
        item.type = self.type
        return {"FINISHED"}

class COATOOLS_OT_RemoveEvent(bpy.types.Operator):
    bl_idname = "coa_tools.remove_event"
    bl_label = "Remove Event"
    bl_description = ""
    bl_options = {"REGISTER"}

    index: IntProperty()
    event_index: IntProperty()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        sprite_object = get_sprite_object(obj)

        anim = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
        timeline_events = anim.timeline_events[self.index]
        timeline_events.event.remove(self.event_index)
        return {"FINISHED"}
    
### Add Timeline Event -> Dragonbones
class COATOOLS_OT_AddTimelineEvent(bpy.types.Operator):
    bl_idname = "coa_tools.add_timeline_event"
    bl_label = "Add Timeline Event"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def change_event_order(self, events):
        for i,event in enumerate(events):
            event_next = None
            if i < len(events)-1:
                event_next = events[i+1]
            if event_next != None and event_next.frame < event.frame:

                events.move(i+1, i)

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        
        anim = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]

        event = None
        for item in anim.timeline_events:
            if item.frame == context.scene.frame_current:
                event = item
                msg = "Timeline Event exists on frame " + str(item.frame) + " already."
                self.report({'INFO'}, msg)
                break
                # return {"FINISHED"}

        if event == None:
            event = anim.timeline_events.add()
            event.frame = context.scene.frame_current
        self.change_event_order(anim.timeline_events)
        for e in anim.timeline_events:
            if e.frame == context.scene.frame_current:
                e.collapsed = False
            else:
                e.collapsed = True
        return {"FINISHED"}
    
        
class COATOOLS_OT_RemoveTimelineEvent(bpy.types.Operator):
    bl_idname = "coa_tools.remove_timeline_event"
    bl_label = "Remove Timeline Event"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    index: IntProperty(default=-1)
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        
        anim = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
        
        if self.index != -1:
            index = self.index
        else:
            index = anim.event_index    
        
        anim.timeline_events.remove(index)
        return {"FINISHED"}
