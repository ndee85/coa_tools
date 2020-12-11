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

import os
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
from .. functions_draw import *        
import traceback

class COATOOLS_OT_TooglePoseMode(bpy.types.Operator):
    bl_idname = "coa_tools.toggle_pose_mode"
    bl_label = "Toggle Mode"
    bl_description = "Toggles between Pose and Object mode."
    bl_options = {"REGISTER"}

    ob_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = bpy.data.objects[self.ob_name]
        active_ob_name = context.active_object.name

        context.view_layer.objects.active = obj
        if obj.mode in ["POSE", "EDIT"]:
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
        elif obj.mode == "OBJECT":
            bpy.ops.object.mode_set(mode="POSE", toggle=False)
        context.view_layer.objects.active = bpy.data.objects[active_ob_name]
        return {"FINISHED"}

class COATOOLS_OT_BindMeshToBones(bpy.types.Operator):
    bl_idname = "coa_tools.bind_mesh_to_bones"
    bl_label = "Bind Mesh To Selected Bones"
    bl_description = "Bind mesh to selected bones."
    bl_options = {"REGISTER"}
    
    ob_name: StringProperty()
    armature = None
    sprite_object = None
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = bpy.data.objects[self.ob_name]
        self.sprite_object = functions.get_sprite_object(obj)
        self.armature = functions.get_armature(self.sprite_object)
        functions.set_weights(self,context,obj)
        
        msg = '"'+obj.name+'"' + " has been bound to selected Bones."
        self.report({'INFO'},msg)
        return {"FINISHED"}
        

######################################################################################################################################### Quick Armature        
class COATOOLS_TO_DrawBone(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_ARMATURE'

    # The prefix of the idname should be your add-on name.
    bl_idname = "coa_tools.draw_bone"
    bl_label = "Draw Bone"
    bl_description = (
        "Draws Bones"
    )
    bl_icon = os.path.join(functions.get_coa_tools_dir(), "icons", "coa_tools.draw_bone")
    bl_widget = None
    # bl_keymap = (
    #     ("coa_tools.draw_polygon", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
    # )

class COATOOLS_OT_QuickArmature(bpy.types.Operator):
    bl_idname = "coa_tools.quick_armature"
    bl_label = "Quick Armature"
    
    def __init__(self):
        self.distance = .1
        self.cur_distance = 0
        self.old_coord = Vector((0,0,0))
        self.mouse_press = False
        self.mouse_press_hist = False
        self.inside_area = False
        self.current_bone = None
        self.object_hover = None
        self.object_hover_hist = None
        self.in_view_3d = False
        self.armature_mode = None
        self.set_waits = False
        self.mouse_click_vec = Vector((0,0,0))
        self.shift = False
        self.shift_hist = False
        self.sprite_object = None
        self.sprite_object_name = ""
        self.alt = False
        self.alt_hist = False
        self.selected_object_names = []
        self.active_object_name = None
        self.armature = None
        self.armature_name = ""
        self.emulate_3_button = False
        self.obj_settings = {}
        
        self.cursor_location = Vector((0,0,0))
        
    def project_cursor(self, event):
        coord = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
        transform = bpy_extras.view3d_utils.region_2d_to_location_3d
        region = bpy.context.region
        rv3d = bpy.context.space_data.region_3d
        #### cursor used for the depth location of the mouse
        depth_location = bpy.context.scene.cursor.location
        #depth_location = bpy.context.active_object.location
        ### creating 3d vector from the cursor
        end = transform(region, rv3d, coord, depth_location)
        #end = transform(region, rv3d, coord, bpy.context.space_data.region_3d.view_location)
        ### Viewport origin
        start = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        ### Cast ray from view to mouselocation
        if functions.b_version_smaller_than((2,91,0)):
            ray = bpy.context.scene.ray_cast(bpy.context.view_layer, start, (start+(end-start)*2000)-start )
        else:
            ray = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, start, (start + (end - start) * 2000) - start)
            
        ### ray_cast return values have changed after blender 2.67.0
        ray = [ray[0],ray[4],ray[5],ray[1],ray[2]]
        
        return start, end, ray
    
    def create_armature(self,context):
        obj = bpy.context.active_object
        sprite_object = functions.get_sprite_object(obj)
        armature = functions.get_armature(sprite_object)
        
        for obj2 in context.selected_objects:
            obj2.select_set(False)
        
        if armature != None:
            context.view_layer.objects.active = armature
            armature.select_set(True)
            return armature
        else:
            amt = bpy.data.armatures.new("Armature")
            armature = bpy.data.objects.new("Armature",amt)
            armature.parent = sprite_object
            context.collection.objects.link(armature)
            context.view_layer.objects.active = armature
            armature.select_set(True)
            armature.show_in_front = True
            #amt.draw_type = "BBONE"
            return armature
        
    def create_default_bone_group(self,armature):
        default_bone_group = None
        if "default_bones" not in armature.pose.bone_groups:
            default_bone_group = armature.pose.bone_groups.new(name="default_bones")
            default_bone_group.color_set = "THEME08"
        else:
            default_bone_group = armature.pose.bone_groups["default_bones"]
        return default_bone_group

    def create_bones(self, context, armature):
        if armature != None:
            
            bpy.ops.object.mode_set(mode='EDIT')
            bone = armature.data.edit_bones.new("Bone")
            
            ### tag bones that will be locked
            bone["lock_z"] = True
            bone["lock_rot"] = True

            head_position = (self.armature.matrix_world.inverted() @ self.mouse_click_vec)
            head_position[1] = 0
            bone.head = head_position
            bone.hide = True
            bone.bbone_x = .05
            bone.bbone_z = .05
            
            for bone2 in armature.data.edit_bones:
                bone2.select_head = False
                bone2.select_tail = False
                if bone2 != armature.data.edit_bones.active:
                    bone2.select = False        
            if armature.data.edit_bones.active != None and armature.data.edit_bones.active.select == True:
                active_bone = armature.data.edit_bones.active
                bone.parent = active_bone
                bone.name = active_bone.name
                distance = Vector(active_bone.tail.xyz - bone.head.xyz).magnitude / bpy.context.space_data.region_3d.view_distance
                if distance < .02:
                    bone.use_connect = True
                    active_bone.select_tail = True
                active_bone.select = False
            
                
            bone.select = True
            bone.select_head = True
            bone.select_tail = True
            armature.data.edit_bones.active = bone
            self.current_bone = bone
            self.create_default_bone_group(armature)    
    
    def drag_bone(self,context, event ,bone=None):
        ### math.atan2(0.5, 0.5)*180/math.pi
        mouse_vec_norm = (self.cursor_location - self.mouse_click_vec).normalized()
        mouse_vec = (self.cursor_location - self.mouse_click_vec)
        angle = (math.atan2(mouse_vec_norm[0], mouse_vec_norm[2]) * 180 / math.pi)
        if bone != None:
            
            bone.hide = False
            cursor_local = self.armature.matrix_world.inverted() @ self.cursor_location
            cursor_local[1] = 0
            if event.shift:
                if angle > -22.5 and angle < 22.5:
                    ### up
                    bone.tail =  Vector((bone.head[0],cursor_local[1],cursor_local[2]))
                elif angle > 22.5 and angle < 67.5:
                    ### up right
                    bone.tail = (bone.head + Vector((mouse_vec[0],0,mouse_vec[0])))
                elif angle > 67.5 and angle < 112.5:
                    ### right
                    bone.tail = Vector((cursor_local[0],cursor_local[1],bone.head[2]))
                elif angle > 112.5 and angle < 157.5:
                    ### down right
                    bone.tail = (bone.head + Vector((mouse_vec[0],0,-mouse_vec[0])))
                elif angle > 157.5 or angle < -157.5:   
                    ### down
                    bone.tail = Vector((bone.head[0],cursor_local[1],cursor_local[2]))
                elif angle > -157.5 and angle < -112.5:
                    ### down left
                        bone.tail = (bone.head + Vector((mouse_vec[0],0,mouse_vec[0])))
                elif angle > -112.5 and angle < -67.5:
                    ### left
                    bone.tail = Vector((cursor_local[0],cursor_local[1],bone.head[2]))
                elif angle > -67.5 and angle < -22.5:       
                    ### left up
                    bone.tail = (bone.head + Vector((mouse_vec[0],0,-mouse_vec[0])))
            else:
                bone.tail = cursor_local
        return mouse_vec.magnitude, mouse_vec.magnitude / bpy.context.space_data.region_3d.view_distance
                 
    def set_parent(self,context,obj):
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.object.parent_set(type='BONE')
        bpy.ops.object.mode_set(mode='EDIT')
        obj.select_set(False)
        bpy.ops.ed.undo_push(message="Sprite "+obj.name+ " set parent")
        
    def return_ray_sprites(self,context,event):
        coord = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
        transform = bpy_extras.view3d_utils.region_2d_to_location_3d
        region = bpy.context.region
        rv3d = bpy.context.space_data.region_3d
        depth_location = Vector((0,50,0))#bpy.context.scene.cursor_location
        end = transform(region, rv3d, coord, depth_location)
        start = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

        return functions.ray_cast(start,end,[])
        
    
    def modal(self, context, event):
        ## skip everything if different tool is selected
        if functions.get_active_tool("EDIT_ARMATURE") != "coa_tools.draw_bone":
            return {'PASS_THROUGH'}

        try:
            self.in_view_3d = functions.check_region(context,event)
                
            if event.alt:
                bpy.context.window.cursor_set("EYEDROPPER") 
            elif not event.alt and self.in_view_3d:    
                bpy.context.window.cursor_set("PAINT_BRUSH")
            else:
                bpy.context.window.cursor_set("DEFAULT")    
                
            scene = context.scene
            ob = context.active_object
            
            
            ### lock posebone scale z value
            self.sprite_object = bpy.data.objects[self.sprite_object_name]
            self.armature = bpy.data.objects[self.armature_name]
            for bone in self.armature.data.bones:
                if "lock_z" in bone:
                    if bone.name in ob.pose.bones:
                        pose_bone = ob.pose.bones[bone.name]
                        pose_bone.lock_scale[2] = True
                        del bone["lock_z"]
                if "lock_rot" in bone:
                    if bone.name in ob.pose.bones:
                        pose_bone = ob.pose.bones[bone.name]
                        pose_bone.lock_rotation[0] = True
                        pose_bone.lock_rotation[1] = True
                        del bone["lock_rot"]        
            
            if self.in_view_3d:
                self.mouse_press_hist = self.mouse_press
                mouse_button = None
                wm = context.window_manager
                keyconfig = wm.keyconfigs.active
                mouse_button = 'LEFTMOUSE'
                ### Set Mouse click
                
                     
                if event.ctrl == False and (event.value == 'PRESS') and event.type == mouse_button and self.mouse_press == False:
                    self.mouse_press = True
                elif event.value in ['RELEASE','NOTHING'] and (event.type == mouse_button):
                    self.mouse_press = False
                ### Cast Ray from mousePosition and set Cursor to hitPoint
                rayStart,rayEnd, ray = self.project_cursor(event)
                
                if ray[0] == True and ray[1] != None:
                    self.cursor_location = ray[3]
                elif rayEnd != None:
                    self.cursor_location = rayEnd
                self.cursor_location[1] = context.active_object.location[1]
                
                if event.value in ["RELEASE"]:
                    if self.object_hover_hist != None:
                        self.object_hover_hist.show_in_front = False
                        self.object_hover_hist.select_set(False)
                        self.object_hover_hist.show_name = False
                        self.object_hover_hist = None
                    if self.object_hover != None:
                        self.object_hover.show_in_front = False
                        self.object_hover.select_set(False)
                        self.object_hover.show_name = False
                            
                    
                if not event.alt and not event.ctrl:
                    self.object_hover = None
                    ### mouse just pressed
                    if not self.mouse_press_hist and self.mouse_press and self.in_view_3d:
                        self.mouse_click_vec = Vector(self.cursor_location)
                    ### mouse pressed
                    elif self.mouse_press_hist and self.mouse_press:
                        drag_distance, drag_distance_normalized = self.drag_bone(context,event,self.current_bone)
                        if drag_distance_normalized > .02 and self.current_bone == None:
                            self.create_bones(context, context.active_object)
                        if context.active_bone != None:
                            bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Y')
                        return {'RUNNING_MODAL'}
                    ### mouse release   
                    elif not self.mouse_press and self.mouse_press_hist and self.current_bone != None:
                        bpy.ops.ed.undo_push(message="Add Bone: "+self.current_bone.name)
                        self.current_bone.hide = False   
                        self.current_bone = None
                        self.mouse_click_vec = Vector((1000000,1000000,1000000))
                        
                        self.set_waits = True
                        bpy.ops.object.mode_set(mode='OBJECT')
                        bpy.ops.object.mode_set(mode='EDIT')
                        self.set_waits = False 
                
                elif (event.alt or "ALT" in event.type) and not event.ctrl and not event.type == "P" and event.type != "A":
                    self.object_hover_hist = self.object_hover
                    
                    hover_objects = self.return_ray_sprites(context,event)
                    distance = 1000000000
                    if len(hover_objects) > 0:
                        for ray in hover_objects:
                            sprite_center = functions.get_bounds_and_center(ray[1])[0]
                            if ((sprite_center) - ray[3]).length < distance:
                                distance = (sprite_center - ray[3]).length
                                self.object_hover = ray[1]
                    else:
                        self.object_hover = None

                    show_in_front = False
                    if self.object_hover != self.object_hover_hist:
                        if self.object_hover != None:
                            self.object_hover.show_name = True
                            self.object_hover.select_set(True)
                            show_in_front = self.object_hover.show_in_front
                            self.object_hover.show_in_front = True
                        if self.object_hover_hist != None:
                            self.object_hover_hist.show_name = False
                            self.object_hover_hist.select_set(False)
                            self.object_hover_hist.show_in_front = False
                    ### mouse just pressed
                    if not self.mouse_press_hist and self.mouse_press and self.in_view_3d and self.object_hover != None:
                        selected_bones = context.selected_editable_bones
                        if ray[0] and ray[1] != None:
                            obj = ray[1]
                            if self.object_hover.coa_tools.type == "MESH":
                                # self.set_weights(context,self.object_hover)
                                functions.set_weights(self, context, self.object_hover)
                                msg = '"' + obj.name + '"' + " has been bound to selected Bones."
                                self.report({'INFO'}, msg)
                            elif self.object_hover.coa_tools.type == "SLOT":
                                prev_index = int(self.object_hover.coa_tools.slot_index)
                                for i, slot in enumerate(self.object_hover.coa_tools.slot):
                                    self.object_hover.coa_tools.slot_index = i
                                    functions.set_weights(self, context, self.object_hover)
                                    msg = '"' + self.object_hover.name + '"' + " has been bound to selected Bones."
                                    self.report({'INFO'}, msg)
                                self.object_hover.coa_tools.slot_index = prev_index 
                    return{'RUNNING_MODAL'}
            
            ### finish mode  
            if context.active_object == None or (context.active_object != None and context.active_object != self.armature) or (context.active_object.mode != "EDIT" and context.active_object.type == "ARMATURE" and self.set_waits == False) or not self.sprite_object.coa_tools.edit_armature:
                return self.exit_edit_mode(context)
            
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"},"An Error occured, please check the console for more information")
            return self.exit_edit_mode(context)
        return {'PASS_THROUGH'}
    
    def exit_edit_mode(self,context):
        functions.set_active_tool(self, context, "builtin.select")
        try:
            bpy.utils.unregister_tool(COATOOLS_TO_DrawBone)
        except:
            pass

        ### remove draw call
        # bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")

        bpy.context.window.cursor_set("CROSSHAIR")

        if context.active_object.type == "ARMATURE":
            bpy.ops.object.mode_set(mode="POSE")

            for pose_bone in context.active_object.pose.bones:
                if "default_bones" in context.active_object.pose.bone_groups and pose_bone.bone_group == None:
                    pose_bone.bone_group = context.active_object.pose.bone_groups["default_bones"]
        
        #lock_sprites(context,get_sprite_object(context.active_object),get_sprite_object(context.active_object).lock_sprites)
        self.sprite_object = bpy.data.objects[self.sprite_object_name]
        self.sprite_object.coa_tools.edit_armature = False
        self.sprite_object.coa_tools.edit_mode = "OBJECT"
        
        ### restore previous selection
        for obj in bpy.context.scene.objects:
            obj.select_set(False)
        for obj_name in self.selected_object_names:
            obj = bpy.data.objects[obj_name] if obj_name in bpy.data.objects else None
            if obj != None:
                obj.select_set(True)
        context.view_layer.objects.active = bpy.data.objects[self.active_object_name] if self.active_object_name in bpy.data.objects else None
        context.preferences.inputs.use_mouse_emulate_3_button = self.emulate_3_button
        
        ### restore object settings
        for obj_name in self.obj_settings:
            obj = bpy.data.objects[obj_name] if obj_name in bpy.data.objects else None
            if obj != None:
                obj.show_name = self.obj_settings[obj_name]["show_name"]
        return{'FINISHED'}
    
    def execute(self, context):
        #bpy.ops.wm.coa_modal() ### start coa modal mode if not running
        self.emulate_3_button = context.preferences.inputs.use_mouse_emulate_3_button
        context.preferences.inputs.use_mouse_emulate_3_button = False
        
        ### store object settings
        for obj in context.scene.objects:
            # self.obj_settings[obj] = {"show_in_front":obj.show_in_front, "show_name":obj.show_name}
            self.obj_settings[obj.name] = {"show_name":obj.show_name}

        for obj in context.scene.objects:
            if obj.select_get():
                self.selected_object_names.append(obj.name)
        self.active_object_name = context.active_object.name
        
        self.sprite_object = functions.get_sprite_object(context.active_object)
        self.sprite_object_name = str(self.sprite_object.name)
        self.sprite_object.coa_tools.edit_armature = True
        self.sprite_object.coa_tools.edit_mode = "ARMATURE"
        
        functions.lock_sprites(context,functions.get_sprite_object(context.active_object),False)
        self.armature = self.create_armature(context)
        self.armature_name = str(self.armature.name)
        
        self.armature.coa_tools.hide = False    
        self.armature_mode = context.active_object.mode
        bpy.ops.object.mode_set(mode='EDIT')

        try:
            bpy.utils.register_tool(COATOOLS_TO_DrawBone, after={"builtin.select"}, separator=True, group=True)
        except:
            pass
        functions.set_active_tool(self, context, "coa_tools.draw_bone")

        context.window_manager.modal_handler_add(self)
        
        ### call draw code
        # args = ()
        # self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, "WINDOW", "POST_PIXEL")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        return {'CANCELLED'}
    
    def draw_callback_px(self):
        pass
        # draw_edit_mode(self,bpy.context,color=[0.461840, 0.852381, 1.000000, 1.000000],text="Edit Armature Mode",offset=0)
    
    
######################################################################################################################################### Set Stretch To Constraint
class COATOOLS_OT_SetStretchBone(bpy.types.Operator):
    bl_idname = "coa_tools.set_stretch_bone"
    bl_label = "Set Stretch Bone"
    
    def execute(self,context):
        armature = context.active_object
        p_bone = armature.pose.bones[context.active_pose_bone.name]
        bpy.ops.object.mode_set(mode="EDIT")
        
        bone_name = "Stretch_"+p_bone.name
        stretch_to_bone = armature.data.edit_bones.new(bone_name)
        stretch_to_bone.use_deform = False
        if p_bone.parent != None:
            stretch_to_bone.parent = context.active_object.data.edit_bones[p_bone.name].parent
        length = Vector(p_bone.tail - p_bone.head).length
        stretch_to_bone.head =  p_bone.tail
        stretch_to_bone.tail = Vector((p_bone.tail[0],0, p_bone.tail[2] + length * .5))
        bpy.ops.object.mode_set(mode="POSE")
        
        stretch_to_constraint = p_bone.constraints.new("STRETCH_TO")
        stretch_to_constraint.target = context.active_object
        stretch_to_constraint.subtarget = bone_name
        stretch_to_constraint.keep_axis = "PLANE_Z" 
        stretch_to_constraint.volume = "VOLUME_X"
        functions.set_bone_group(self, context.active_object, context.active_object.pose.bones[bone_name],group="stretch_to",theme = "THEME07")
        return{'FINISHED'}

######################################################################################################################################### Set IK Constraint 

class COATOOLS_OT_RemoveIK(bpy.types.Operator):
    bl_idname = "coa_tools.remove_ik"
    bl_label = "Remove IK"
    bl_description = "Remove Bone IK"
    bl_options = {"REGISTER"}


    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.active_object
        pose_bone = bpy.context.active_pose_bone
        if obj.type == "ARMATURE":
            
            ik_const_found = False
            for bone in obj.pose.bones:
                for const in bone.constraints:
                    if const.type == "IK" and const.subtarget == pose_bone.name:
                        ik_const_found = True
            if ik_const_found == False:
                self.report({"WARNING"}, "No IK Constraint found to delete.")
                return{"CANCELLED"}            
                        
            
            for bone in obj.pose.bones:
                copy_loc = None
                copy_rot = None
                
                for const in bone.constraints:
                    if const.type == "COPY_LOCATION" and const.subtarget == pose_bone.name:
                        copy_loc = const
                    if const.type == "COPY_ROTATION" and const.subtarget == pose_bone.name:
                        copy_rot = const
                    if const.type == "IK":
                        if const.subtarget == pose_bone.name:
                            bone.constraints.remove(const)
                if copy_loc != None and copy_rot != None:
                    bone.constraints.remove(copy_loc)
                    bone.constraints.remove(copy_rot)
                    obj.data.bones[bone.name].layers[0] = True
                    obj.data.bones[bone.name].layers[1] = False
                    obj.data.bones.active = obj.data.bones[bone.name]
                    obj.data.bones[bone.name].select = True
                    
            bpy.ops.object.mode_set(mode="EDIT")
            obj.data.edit_bones.remove(obj.data.edit_bones[pose_bone.name])
            bpy.ops.object.mode_set(mode="POSE")
                            
            
        return {"FINISHED"}
        

class COATOOLS_OT_SetIK(bpy.types.Operator):
    bl_idname = "coa_tools.set_ik"
    bl_label = "Set IK Bone"
    
    replace_bone: BoolProperty(name="Replace IK Bone",description="Replaces active Bone as IK Bone", default=True)
    
    def invoke(self, context, event):
        wm = context.window_manager 
        return wm.invoke_props_dialog(self)   

    def execute(self,context):
        bone = context.active_object.pose.bones[context.active_pose_bone.name]
        bone2 = context.selected_pose_bones[0]
        ik_bone = None
        if self.replace_bone:
            ik_bone = bone.parent
        else:
            ik_bone = bone  
        next_bone = bone
        ik_length = 0
        while next_bone != bone2 and next_bone.parent != None:
            ik_length += 1 
            next_bone = next_bone.parent
        if not self.replace_bone:
            ik_length += 1
        
        for bone3 in context.active_object.data.bones:
            bone3.select = False
            
        bpy.ops.object.mode_set(mode="EDIT")
        ik_target_name = "IK_" + bone.name
        ik_target = context.active_object.data.edit_bones.new("IK_" + bone.name)
        if bone.parent != None:
            ik_target.parent = context.active_object.data.edit_bones[bone.name].parent_recursive[len(context.active_object.data.edit_bones[bone.name].parent_recursive)-1]
        if self.replace_bone:
            ik_target.head = bone.head
            ik_target.tail = bone.tail
        else:
             ik_target.head = bone.tail
             ik_target.tail = ik_target.head + Vector(((bone.tail - bone.head).length,0,0)) 
        ik_target.roll = context.active_object.data.edit_bones[bone.name].roll
        bpy.ops.object.mode_set(mode="POSE")
        context.active_object.data.bones[ik_target_name].select = True
        context.active_object.data.bones.active = context.active_object.data.bones[ik_target_name]
        
        ik_bone.lock_ik_x = True
        ik_bone.lock_ik_y = True
        #ik_bone.ik_stiffness_z = .9
        ik_const = ik_bone.constraints.new("IK")
        ik_const.target = context.active_object
        ik_const.subtarget = ik_target_name
        ik_const.chain_count = ik_length
        
        functions.set_bone_group(self, context.active_object, context.active_object.pose.bones[ik_target_name])
        
        if self.replace_bone:
            copy_loc_const = bone.constraints.new("COPY_LOCATION")
            copy_loc_const.target = context.active_object
            copy_loc_const.subtarget = ik_target_name
            
            copy_rot_const = bone.constraints.new("COPY_ROTATION")
            copy_rot_const.target = context.active_object
            copy_rot_const.subtarget = ik_target_name
            context.active_object.data.bones[bone.name].layers[1] = True
            context.active_object.data.bones[bone.name].layers[0] = False
            
        bpy.ops.ed.undo_push(message="Set Ik")
        return{'FINISHED'}
    
class COATOOLS_OT_CreateStretchIK(bpy.types.Operator):
    bl_idname = "coa_tools.create_stretch_ik"
    bl_label = "Create Stretch Ik"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def get_bones(self,context,bones):
        p_bone = bones[0] ### parent bone
        c_bone = bones[0] ### control bone
        ik_bone = bones[0]
        while p_bone.parent in bones:
            p_bone = p_bone.parent
        while len(c_bone.children) > 0 and c_bone.children[0] in bones:
            c_bone = c_bone.children[0]
        
        ik_bones = []
        ik_bone = p_bone.children[0]
        while ik_bone not in ik_bones and ik_bone != c_bone:
            ik_bones.append(ik_bone)
            for child in ik_bone.children:
                if child.select:
                    ik_bone = child
                    break
        
        return [p_bone,c_bone,ik_bones]
    
    def duplicate_bones(self,context,bones):
        bpy.ops.armature.select_all(action='DESELECT')
        new_bones = []
        for i,bone in enumerate(bones):
            new_bone = context.active_object.data.edit_bones.new(bone.name + "_CTRL")
            new_bone.roll = bone.roll
            new_bone.tail = bone.tail
            new_bone.head = bone.head
            new_bones.append(new_bone)
            
            if i == 0:
                new_bone.parent = bone.parent
            else:
                new_bone.use_connect = True
                new_bone.parent = new_bones[i-1]
            new_bone.select = True
            new_bone.select_head = True
            new_bone.select_tail = True
        return new_bones         
        
        
    def execute(self, context):
        obj = context.active_object
        
        if len(context.selected_pose_bones) < 3:
            self.report({'WARNING'},"Select 3 bones at least.")
            return{"CANCELLED"}
        
        ####################### create all needed bones #######################
        
        bpy.ops.object.mode_set(mode="EDIT")
        bones = context.selected_bones[:]
        
        ### get deform bones
        p_bone_def, c_bone_def, ik_bones_def = self.get_bones(context,bones)
        
        ### duplicate deform bones
        self.duplicate_bones(context,[p_bone_def]+ik_bones_def+[c_bone_def])
        ### get control bones
        bones = context.selected_bones[:]
        p_bone_ctrl, c_bone_ctrl, ik_bones_ctrl = self.get_bones(context,bones)
        p_bone_ctrl.name = p_bone_def.name + "_CTRL"
        c_bone_ctrl.name = c_bone_def.name + "_CTRL"
        for i,ik_bone in enumerate(ik_bones_ctrl):
            ik_bone.name = ik_bones_def[i].name + "_CTRL"
        c_bone_ctrl.use_connect = False
        c_bone_ctrl.parent = None
            
        
        ### create stretch to bone
        joint_bones_ctrl = []
        for i,ik_bone in enumerate(ik_bones_ctrl):
            joint_bone_ctrl = context.active_object.data.edit_bones.new(ik_bones_def[i].name+ "_JOINT")
            joint_bone_ctrl.head = ik_bone.head
            joint_bone_ctrl.tail = ik_bone.head + Vector((-1,0,0))
            joint_bone_ctrl.parent = ik_bone.parent#p_bone_ctrl
            joint_bone_ctrl.use_connect = False
            joint_bone_ctrl.select = True
            joint_bone_ctrl.select_head = True
            joint_bone_ctrl.select_tail = True
            joint_bone_ctrl.use_inherit_scale = False
            joint_bone_ctrl.use_inherit_rotation = False
            joint_bones_ctrl.append(joint_bone_ctrl)
        
        ####################### create all needed constraints #######################
        
        ### get names from edit bone names while in edit mode. Otherwise Editbones will not be available to gather name from
        p_bone_ctrl_name = str(p_bone_ctrl.name)
        c_bone_ctrl_name = str(c_bone_ctrl.name)
        
        ik_bone_ctrl_names = []
        for ik_bone in ik_bones_ctrl:
            ik_bone_ctrl_names.append(str(ik_bone.name))
        
        p_bone_def_name = str(p_bone_def.name)
        c_bone_def_name = str(c_bone_def.name)
        
        ik_bone_def_names = []
        for ik_bone in ik_bones_def:
            ik_bone_def_names.append(str(ik_bone.name))
        
        ik_bone_ctrl_names = []
        for ik_bone in ik_bones_ctrl:
            ik_bone_ctrl_names.append(str(ik_bone.name))
        
        joint_bone_ctrl_names = []
        for join_bone in joint_bones_ctrl:
            joint_bone_ctrl_names.append(str(join_bone.name))
        
        ### change mode into pose mode
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.object.mode_set(mode="POSE")

        ### get pose def bones
        p_bone_def = obj.pose.bones[p_bone_def_name]
        c_bone_def = obj.pose.bones[c_bone_def_name]
        ik_bones_def =  []
        for ik_bone_name in ik_bone_def_names:
            ik_bones_def.append(obj.pose.bones[ik_bone_name])
        
        ### get pose ctrl bones
        p_bone_ctrl = obj.pose.bones[p_bone_ctrl_name]
        c_bone_ctrl = obj.pose.bones[c_bone_ctrl_name]
        ik_bones_ctrl = []
        for ik_bone_name in ik_bone_ctrl_names:
            ik_bones_ctrl.append(obj.pose.bones[ik_bone_name])
        
        joint_bones_ctrl = []
        for joint_bone_name in joint_bone_ctrl_names:
            joint_bones_ctrl.append(obj.pose.bones[joint_bone_name])
        
        ### disable deforming for all ctrl bones
        ctrl_bones = [p_bone_ctrl, c_bone_ctrl] + ik_bones_ctrl + joint_bones_ctrl
        for bone in ctrl_bones:
            bone = obj.data.bones[bone.name]
            bone.use_deform = False
        
        c = p_bone_def.constraints.new("LIMIT_ROTATION")
        c.owner_space = "POSE"
        c.use_limit_z = True
        
        c = p_bone_def.constraints.new("STRETCH_TO")
        c.target = obj
        c.subtarget = joint_bones_ctrl[0].name
        c.keep_axis = "PLANE_Z"
        const_p_bone = c
        
        
        c = p_bone_def.constraints.new("LIMIT_SCALE")
        c.owner_space = "POSE"
        c.use_min_z = True
        c.use_max_z = True
        c.max_z = 1.0
        c.min_z = 1.0
        
        const_ik_bones = []
        for i,ik_bone_def in enumerate(ik_bones_def):
            c = ik_bone_def.constraints.new("LIMIT_ROTATION")
            c.owner_space = "POSE"
            c.use_limit_z = True
            
            c = ik_bone_def.constraints.new("STRETCH_TO")
            c.target = obj
            c.keep_axis = "PLANE_Z"
            const_ik_bones.append(c)
            if i == len(ik_bones_def)-1:
                c.subtarget = c_bone_ctrl.name
            else:    
                c.subtarget = joint_bones_ctrl[i+1].name
            
            c = ik_bone_def.constraints.new("LIMIT_SCALE")
            c.owner_space = "POSE"
            c.use_min_z = True
            c.use_max_z = True
            c.max_z = 1.0
            c.min_z = 1.0
                
                
        c = c_bone_def.constraints.new("COPY_TRANSFORMS")
        c.target = obj
        c.subtarget = c_bone_ctrl.name
        const_c_bone = c
        
        c = ik_bones_ctrl[len(ik_bones_ctrl)-1].constraints.new("IK")
        c.target = obj
        c.subtarget = c_bone_ctrl.name
        c.chain_count = len(ik_bones_ctrl) + 1
        const_ik = c
        
        for ik_bone_ctrl in ik_bones_ctrl:
            ik_bone_ctrl.lock_ik_x = True
            ik_bone_ctrl.lock_ik_y = True
        
            ik_bone_ctrl.ik_stretch = .2
        p_bone_ctrl.ik_stretch = .2
        
        ### move bones to other layers
        hide_bone_names = [p_bone_ctrl_name, p_bone_def_name, c_bone_def_name] + ik_bone_ctrl_names + ik_bone_def_names
        for bone_name in hide_bone_names:
            obj.data.bones[bone_name].layers[1] = True
            obj.data.bones[bone_name].layers[0] = False
        
        ### store bones and constraints in Stretch IK Pointer Property
        p_bone_def["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"p_bone_def"])
        c_bone_def["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"c_bone_def"])
        for ik_bone_def in ik_bones_def:
            ik_bone_def["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"ik_bone_def"])
        
        p_bone_ctrl["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"p_bone_ctrl"])
        c_bone_ctrl["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"c_bone_ctrl"])
        
        for ik_bone_ctrl in ik_bones_ctrl:
            ik_bone_ctrl["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"ik_bone_ctrl"])
        for joint_bone_ctrl in joint_bones_ctrl:
            joint_bone_ctrl["coa_stretch_ik_data"] = str([c_bone_ctrl.name,"joint_bone_ctrl"])
        
        ### set bone colors
        functions.set_bone_group(self, obj, c_bone_ctrl,group = "ik_group" ,theme = "THEME09")
        for joint_bone_ctrl in joint_bones_ctrl:
            functions.set_bone_group(self, obj, joint_bone_ctrl,group = "ik_group" ,theme = "THEME09")
        
        return {"FINISHED"}
    
class COATOOLS_OT_RemoveStretchIK(bpy.types.Operator):
    bl_idname = "coa_tools.remove_stretch_ik"
    bl_label = "Remove Stretch Ik"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    stretch_ik_name: StringProperty()
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.active_object
        bpy.ops.object.mode_set(mode="EDIT")
        
        for bone in obj.pose.bones:
            e_bone = obj.data.edit_bones[bone.name]
            if "coa_stretch_ik_data" in bone:
                name = eval(bone["coa_stretch_ik_data"])[0]
                type = eval(bone["coa_stretch_ik_data"])[1]
                
                if name == self.stretch_ik_name:
                    if "_ctrl" in type:
                        obj.data.edit_bones.remove(e_bone)
                    elif "_def" in type:
                        for const in bone.constraints:
                            bone.constraints.remove(const)    
                        
                        bpy.ops.object.mode_set(mode="POSE") 
                        
                        del(bone["coa_stretch_ik_data"])
                        
                        bone = obj.data.bones[bone.name]
                        bone.select = True
                        obj.data.bones.active = bone
                        bone.layers[0] = True
                        bone.layers[1] = False
                        
                        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.object.mode_set(mode="POSE")            
        
        return {"FINISHED"}
