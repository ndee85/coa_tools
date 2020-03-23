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
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty, PointerProperty
import os
from bpy_extras.io_utils import ExportHelper, ImportHelper
import json
from . import functions
from . import addon_updater_ops
from . outliner import *
#from . import preview_collections

bone_layers = []
armature_mode = None
armature_select = False

class COATOOLS_OT_ChangeShadingMode(bpy.types.Operator):
    bl_idname = "coa_tools.change_shading_mode"
    bl_label = "Change Shading Mode"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        context.scene.eevee.use_taa_reprojection = False
        context.space_data.shading.type = 'RENDERED'
        context.scene.view_settings.view_transform = "Standard"
        return {"FINISHED"}


class COATOOLS_PT_Info(bpy.types.Panel):
    bl_idname = "COATOOLS_PT_social"
    bl_label = "Info Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "COA Tools"

    @classmethod
    def poll(cls, context):
        if addon_updater_ops.updater.update_ready and addon_updater_ops.updater.json["ignore"] == False:
            return context
        if context.scene.coa_tools.deprecated_data_found:
            return context
        if context.space_data.shading.type != "RENDERED" or context.scene.view_settings.view_transform != "Standard":
            return context



    def draw(self, context):

        layout = self.layout

        if context.scene.coa_tools.deprecated_data_found:
            row = layout.row()
            row.operator("coa_tools.convert_deprecated_data", icon="LIBRARY_DATA_BROKEN")

        if (context.space_data.shading.type != "RENDERED" or context.scene.view_settings.view_transform != "Standard") and not context.scene.coa_tools.deprecated_data_found:
            row = layout.row()
            row.operator("coa_tools.change_shading_mode", text="Set Textured Shading Mode", icon="ERROR")

        # if functions.get_addon_prefs(context).show_donate_icon:
        #     row = layout.row()
        #     row.alignment = "CENTER"
        #
        #     pcoll = preview_collections["main"]
        #     donate_icon = pcoll["donate_icon"]
        #     twitter_icon = pcoll["twitter_icon"]
        #     row.operator("coa_operator.coa_donate",text="Show Your Love",icon_value=donate_icon.icon_id,emboss=True)
        #     row = layout.row()
        #     row.alignment = "CENTER"
        #     row.scale_x = 1.75
        #     op = row.operator("coa_operator.coa_tweet",text="Tweet",icon_value=twitter_icon.icon_id,emboss=True)
        #     op.link = "https://www.youtube.com/ndee85"
        #     op.text = "Check out CutoutAnimation Tools Addon for Blender by Andreas Esau."
        #     op.hashtags = "b3d,coatools"
        #     op.via = "ndee85"

        addon_updater_ops.update_notice_box_ui(self, context)

last_obj = None
class COATOOLS_PT_ObjectProperties(bpy.types.Panel):
    bl_idname = "COATOOLS_PT_object_properties"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Object Properties"
    bl_category = "COA Tools"

    @classmethod
    def poll(cls, context):
        if not context.scene.coa_tools.deprecated_data_found:
            return context

    def draw_outliner(self, context, layout, sprite_object, scene):
        ### new Outliner
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="", icon="OUTLINER")
        row.prop(context.scene.coa_tools, "outliner_filter_names", text="", icon="VIEWZOOM")
        if context.scene.coa_tools.outliner_favorites:
            row.prop(context.scene.coa_tools, "outliner_favorites", text="", icon="SOLO_ON")
        else:
            row.prop(context.scene.coa_tools, "outliner_favorites", text="", icon="SOLO_OFF")

        row = col.row()
        row.template_list("COATOOLS_UL_Outliner", "", scene.coa_tools, "outliner", scene.coa_tools, "outliner_index",
                          rows=10)
        row = col.row()
        if sprite_object != None:
            if sprite_object.coa_tools.edit_mesh:
                row.prop(sprite_object.coa_tools, "edit_mesh", text="", toggle=True, icon="LOOP_BACK")
            if sprite_object.coa_tools.edit_armature:
                row.prop(sprite_object.coa_tools, "edit_armature", text="", toggle=True, icon="LOOP_BACK")
            if sprite_object.coa_tools.edit_weights:
                row.prop(sprite_object.coa_tools, "edit_weights", text="", toggle=True, icon="LOOP_BACK")
            if sprite_object.coa_tools.edit_shapekey:
                row.prop(sprite_object.coa_tools, "edit_shapekey", text="", toggle=True, icon="LOOP_BACK")
        ###

    def draw(self, context):
        global last_obj

        layout = self.layout
        obj = context.active_object
        if obj != None:
            last_obj = obj.name
        elif obj == None and last_obj != None and last_obj in bpy.data.objects:
            obj = bpy.data.objects[last_obj] if last_obj in bpy.data.objects else None
        sprite_object = functions.get_sprite_object(obj)
        scene = context.scene

        # functions.display_children(self, context, obj)
        self.draw_outliner(context, layout, sprite_object, scene)

        if sprite_object != None and obj != None:
            row = layout.row(align=True)

            col = row.column(align=True)

            icon = "NONE"
            if obj.type == "ARMATURE":
                icon = "ARMATURE_DATA"
            elif obj.type == "MESH":
                icon = "OBJECT_DATA"
            elif obj.type == "LAMP":
                icon = "LAMP"

            col.prop(obj, "name", text="", icon=icon)
            if obj.type == "MESH" and obj.coa_tools.type == "SLOT":
                index = min(len(obj.coa_tools.slot) - 1, obj.coa_tools.slot_index)
                col.prop(obj.coa_tools.slot[index].mesh,"name",text="",icon="OUTLINER_DATA_MESH")
            if obj.type == "ARMATURE":
                row = layout.row(align=True)
                if context.active_bone != None:

                    col.prop(context.active_bone, 'name', text="", icon="BONE_DATA")
                    ### remove bone ik constraints
                    pose_bone = context.active_pose_bone
                    if pose_bone != None and context.active_object != None:
                        for bone in context.active_object.pose.bones:
                            for const in bone.constraints:
                                if const.type == "IK":
                                    if const.subtarget == pose_bone.name:
                                        row = col.row()
                                        row.operator("coa_tools.remove_ik",text="Remove Bone IK", icon="CONSTRAINT_BONE")



                    ### remove bone stretch ik constraints
                    if context.active_pose_bone != None and "coa_stretch_ik_data" in context.active_pose_bone:
                        col = layout.box().column(align=True)

                        for bone in obj.pose.bones:
                            if "coa_stretch_ik_data" in bone:
                                if eval(bone["coa_stretch_ik_data"])[0] == eval(context.active_pose_bone["coa_stretch_ik_data"])[0]:
                                    if "c_bone_ctrl" == eval(bone["coa_stretch_ik_data"])[1]:
                                        row = col.row()
                                        row.label(text="Stretch IK Constraint",icon="CONSTRAINT_BONE")
                                        op = row.operator("coa_tools.remove_stretch_ik",icon="X",emboss=False, text="")
                                        op.stretch_ik_name = eval(bone["coa_stretch_ik_data"])[0]
                                    elif eval(bone["coa_stretch_ik_data"])[1] in ["ik_bone_ctrl","p_bone_ctrl"]:
                                        col.prop(bone,"ik_stretch",text=bone.name)

            if obj != None and obj.type == "MESH" and obj.mode == "OBJECT":
                row = layout.row(align=True)
                row.label(text="Sprite Properties:")

            if obj != None and obj.type == "MESH" and "coa_base_sprite" in obj.modifiers:
                row = layout.row(align=True)
                row.prop(obj.data.coa_tools, 'hide_base_sprite', text="Hide Base Sprite")
                if len(obj.data.vertices) > 4 and obj.data.coa_tools.hide_base_sprite == False:
                    row.prop(obj.data.coa_tools, 'hide_base_sprite', text="", icon="ERROR", emboss=False)
                # row = layout.row(align=True)
                # row.prop(obj.coa_tools, 'blend_mode',text="", expand=False)
            if obj != None and obj.type == "MESH" and obj.mode == "OBJECT":
                row = layout.row(align=True)
                if obj.coa_tools.type == "SLOT":
                    text = str(len(obj.coa_tools.slot)) + " Slot(s) total"
                    row.label(text=text)

                if obj.coa_tools.type == "SLOT" and len(obj.coa_tools.slot) > 0:
                    row = layout.row(align=True)
                    slot_text = "Slot Index (" + str(len(obj.coa_tools.slot)) + ")"
                    row.prop(obj.coa_tools,'slot_index',text="Slot Index")
                    op = row.operator("coa_tools.select_frame_thumb",text="",icon="IMAGE_RGB")
                    op = row.operator("coa_tools.add_keyframe",text="",icon="KEYTYPE_MOVING_HOLD_VEC")
                    op.prop_name = "coa_tools.slot_index"
                    op.add_keyframe = True
                    op.default_interpolation = "CONSTANT"
                    op = row.operator("coa_tools.add_keyframe",text="",icon="HANDLETYPE_ALIGNED_VEC")
                    op.prop_name = "coa_tools.slot_index"
                    op.add_keyframe = False

            if obj != None and obj.type == "MESH" and obj.mode == "OBJECT":
                row = layout.row(align=True)
                row.prop(obj.coa_tools ,'z_value',text="Z Depth")
                op = row.operator("coa_tools.add_keyframe",text="",icon="KEYTYPE_MOVING_HOLD_VEC")
                op.prop_name = "coa_tools.z_value"
                op.add_keyframe = True
                op.default_interpolation = "CONSTANT"
                op = row.operator("coa_tools.add_keyframe",text="",icon="HANDLETYPE_ALIGNED_VEC")
                op.prop_name = "coa_tools.z_value"
                op.add_keyframe = False

                row = layout.row(align=True)
                row.prop(obj.coa_tools,'alpha',text="Alpha",icon="TEXTURE")
                op = row.operator("coa_tools.add_keyframe",text="",icon="KEYTYPE_MOVING_HOLD_VEC")
                op.prop_name = "coa_tools.alpha"
                op.add_keyframe = True
                op.default_interpolation = "BEZIER"
                op = row.operator("coa_tools.add_keyframe",text="",icon="HANDLETYPE_ALIGNED_VEC")
                op.prop_name = "coa_tools.alpha"
                op.add_keyframe = False

                row = layout.row(align=True)
                row.prop(obj.coa_tools,'modulate_color',text="")
                op = row.operator("coa_tools.add_keyframe",text="",icon="KEYTYPE_MOVING_HOLD_VEC")
                op.prop_name = "coa_tools.modulate_color"
                op.add_keyframe = True
                op.default_interpolation = "LINEAR"
                op = row.operator("coa_tools.add_keyframe",text="",icon="HANDLETYPE_ALIGNED_VEC")
                op.prop_name = "coa_tools.modulate_color"
                op.add_keyframe = False

        if obj != None and obj.type == "CAMERA":
            row = layout.row(align=True)
            row.label(text="Camera Properties:")
            row = layout.row(align=True)
            row.prop(obj.data,"ortho_scale",text="Camera Zoom")
            row = layout.row(align=True)
            rd = context.scene.render
            col = row.column(align=True)
            col.label(text="Resolution:")
            col.prop(rd, "resolution_x", text="X")
            col.prop(rd, "resolution_y", text="Y")
            col.prop(rd, "resolution_percentage", text="")

            col.label(text="Path:")
            col.prop(rd, "filepath", text="")

            row = layout.row(align=True)
            col = row.column(align=True)
            col.prop(obj, "location")

######################################################################################################################################### Cutout Animation Tools Panel
class COATOOLS_PT_Tools(bpy.types.Panel):
    bl_idname = "COATOOLS_PT_tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Cutout Tools"
    bl_category = "COA Tools"

    bpy.types.WindowManager.coa_show_help: BoolProperty(default=False,description="Hide Help")

    @classmethod
    def poll(cls, context):
        if not context.scene.coa_tools.deprecated_data_found:
            return context

    def draw(self, context):
        global last_obj
        wm = context.window_manager
        layout = self.layout
        obj = context.active_object
        if obj == None and last_obj != None and last_obj in bpy.data.objects:
            obj = bpy.data.objects[last_obj]

        sprite_object = functions.get_sprite_object(obj)
        scene = context.scene

        row = layout.row(align=True)
        row.prop(scene.coa_tools, "view", expand=True)

        if not wm.coa_tools.show_help:
            row.operator("coa_tools.show_help", text="", icon="INFO")
        else:
            row.prop(wm.coa_tools, "show_help", text="", icon="INFO")

        if obj != None and sprite_object != None:
            ### draw Edit Mode Operator
            if obj.mode in ["OBJECT", "POSE"]:
                row = layout.row()
                row.label(text="Edit Modes:")

            if sprite_object.coa_tools.edit_mesh == False and sprite_object.coa_tools.edit_shapekey == False and sprite_object.coa_tools.edit_armature == False and sprite_object.coa_tools.edit_weights == False and obj.mode not in ["SCULPT"]:
                row = layout.row(align=True)
                op = row.operator("coa_tools.edit_mesh", text="Edit Mesh", icon="GREASEPENCIL")
                op.mode = "EDIT_MESH"

            if sprite_object.coa_tools.edit_mesh == False and sprite_object.coa_tools.edit_shapekey == False and sprite_object.coa_tools.edit_armature == False and sprite_object.coa_tools.edit_weights == False and not (
                    obj.type == "MESH" and obj.mode in ["EDIT", "SCULPT"]):
                row = layout.row(align=True)
                row.operator("coa_tools.quick_armature", text="Edit Armature", icon="ARMATURE_DATA")
            elif sprite_object.coa_tools.edit_armature:
                row = layout.row(align=True)
                row.prop(sprite_object.coa_tools, "edit_armature", text="Finish Edit Armature", icon="ARMATURE_DATA")

            if sprite_object.coa_tools.edit_mesh == False and sprite_object.coa_tools.edit_shapekey == False and sprite_object.coa_tools.edit_armature == False and sprite_object.coa_tools.edit_weights == False and obj.mode not in [
                "SCULPT"]:
                row = layout.row(align=True)
                row.operator("coa_tools.edit_shapekey", text="Edit Shapekey", icon="SHAPEKEY_DATA")

            if sprite_object.coa_tools.edit_mesh == False and sprite_object.coa_tools.edit_shapekey == False and sprite_object.coa_tools.edit_armature == False and sprite_object.coa_tools.edit_weights == False and not (
                    obj.type == "MESH" and obj.mode in ["EDIT", "SCULPT"]) and (sprite_object) != None:
                row = layout.row(align=True)
                row.operator("coa_tools.edit_weights", text="Edit Weights", icon="MOD_VERTEX_WEIGHT")
            elif sprite_object.coa_tools.edit_weights:
                row = layout.row(align=True)
                row.prop(sprite_object.coa_tools, "edit_weights", text="Finish Edit Weights", toggle=True,
                         icon="MOD_VERTEX_WEIGHT")
            ###

        no_edit_mode_active = sprite_object != None and sprite_object.coa_tools.edit_shapekey == False and sprite_object.coa_tools.edit_mesh == False and sprite_object.coa_tools.edit_armature == False and sprite_object.coa_tools.edit_weights == False
        if obj == None or (obj != None):
            if sprite_object != None and sprite_object.coa_tools.edit_mesh:
                row = layout.row(align=True)
                row.prop(sprite_object.coa_tools, "edit_mesh", text="Finish Edit Mesh", toggle=True, icon="GREASEPENCIL")
            elif sprite_object != None and sprite_object.coa_tools.edit_shapekey:
                row = layout.row(align=True)
                row.prop(sprite_object.coa_tools, "edit_shapekey", text="Finish Edit Shapekey", toggle=True,
                         icon="SHAPEKEY_DATA")

            if obj != None and obj.mode in ["OBJECT", "POSE"] and no_edit_mode_active:
                row = layout.row(align=True)
                row.label(text="General Operator:")

                row = layout.row(align=True)
                op = row.operator("coa_tools.create_ortho_cam", text="Create Camera", icon="OUTLINER_DATA_CAMERA")
                op.create = True
        if obj != None and obj.type == "CAMERA":
            row = layout.row(align=True)
            op = row.operator("coa_tools.create_ortho_cam", text="Reset Camera Resolution", icon="OUTLINER_DATA_CAMERA")
            op.create = False

        if obj == None or (obj != None and obj.mode not in ["EDIT", "WEIGHT_PAINT", "SCULPT"]):
            row = layout.row(align=True)
            row.operator("coa_tools.create_sprite_object", text="Create new Sprite Object", icon="TEXTURE_DATA")
        if obj != None and obj.type == "ARMATURE" and "sprite_object" not in obj.coa_tools:
            row = layout.row(align=True)
            row.operator("coa_tools.define_sprite_object", text="Define as Sprite Object", icon="TEXTURE_DATA")

        if sprite_object != None:
            if obj != None and obj.mode in ["OBJECT", "SCULPT", "POSE"]:
                if functions.operator_exists("object.create_driver_constraint") and len(context.selected_objects) > 1:
                    row = layout.row()
                    row.operator("object.create_driver_constraint", text="Driver Constraint", icon="DRIVER")

            if sprite_object.coa_tools.edit_weights == False and sprite_object.coa_tools.edit_shapekey == False:
                if sprite_object != None and (
                        (obj != None and obj.mode not in ["EDIT", "WEIGHT_PAINT", "SCULPT"]) or obj == None):
                    row = layout.row(align=True)
                    row.operator("coa_tools.import_sprites", text="Re / Import Sprites", icon="FILEBROWSER")


                    row = layout.row(align=True)
                    row.operator("coa_tools.create_slot_object", text="Merge to Slot Object", icon="FILEBROWSER",emboss=True)
                    if obj != None and obj.coa_tools.type == "SLOT":
                        row.operator("coa_tools.extract_slots", text="Extract Slots", icon="EXPORT", emboss=True)

                    row = layout.row()
                    row.operator("coa_tools.change_alpha_mode", text="Change Alpha Mode", icon="SHADING_RENDERED")
                    row = layout.row()
                    row.operator("coa_tools.change_texture_interpolation_mode", text="Change Texture Mode", icon="NODE_TEXTURE")

                    if functions.operator_exists("object.create_driver_constraint") and len(context.selected_objects) > 1:
                        row = layout.row()
                        row.operator("object.create_driver_constraint", text="Driver Constraint", icon="DRIVER")

                if obj != None:
                    if obj.type == "ARMATURE" and obj.mode == "POSE":
                        row = layout.row(align=True)
                        row.operator("coa_tools.draw_bone_shape", text="Draw Bone Shape", icon="BONE_DATA")

                    if obj != None and obj.mode == "POSE":
                        row = layout.row(align=True)
                        row.label(text="Bone Constraint Operator:")
                        row = layout.row(align=True)
                        row.operator("coa_tools.set_ik", text="Create IK Bone", icon="CONSTRAINT_BONE")
                        row = layout.row(align=True)
                        row.operator("coa_tools.set_stretch_bone", text="Create Stretch Bone", icon="CONSTRAINT_BONE")

                        row = layout.row(align=True)
                        row.operator("coa_tools.create_stretch_ik", text="Create Stretch IK", icon="CONSTRAINT_BONE")

            if obj != None and obj.type == "MESH":

                if obj != None and obj.mode == "SCULPT":
                    if not sprite_object.coa_tools.edit_shapekey:
                        row = layout.row(align=True)
                        row.operator("coa_tools.leave_sculptmode", text="Finish Edit Shapekey", icon="SHAPEKEY_DATA")
                    row = layout.row(align=True)
                    functions.draw_sculpt_ui(self, context, row)

                if sprite_object.coa_tools.edit_mesh == False and sprite_object.coa_tools.edit_shapekey == False and sprite_object.coa_tools.edit_armature == False and sprite_object.coa_tools.edit_weights == False and not (
                        obj.type == "MESH" and obj.mode in ["EDIT", "SCULPT"]) and (sprite_object) != None:
                    pass
                elif sprite_object.coa_tools.edit_weights:
                    col = layout.split().column()
                    tool_settings = scene.tool_settings
                    brush_data = tool_settings.weight_paint

                    col.template_ID_preview(brush_data, "brush", new="brush.add", rows=3, cols=8)
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings, "weight")
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings, "size")
                    row.prop(tool_settings.unified_paint_settings, "use_pressure_size", text="")
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings, "strength")
                    row.prop(tool_settings.unified_paint_settings, "use_pressure_strength", text="")
                    row = col.row(align=True)
                    row.prop(tool_settings, "use_auto_normalize", text="Auto Normalize")

        if obj != None and obj.mode == "EDIT" and obj.type == "MESH" and sprite_object.coa_tools.edit_mesh:
            row = layout.row(align=True)
            row.label(text="Mesh Tools:")

            row = layout.row(align=True)
            operator = row.operator("coa_tools.generate_mesh_from_edges_and_verts", text="Generate Mesh", icon="OUTLINER_OB_SURFACE")

            col = layout.column(align=True)

            row2 = col.row(align=True)
            row2.prop(scene.coa_tools, 'distance', text="Stroke Distance")
            row2.operator("coa_tools.pick_edge_length", text="", icon="EYEDROPPER")

            row2 = col.row(align=True)
            row2.prop(scene.coa_tools, 'snap_distance', text="Snap Distance")
            row2 = col.row(align=True)
            if scene.coa_tools.surface_snap:
                row2.prop(scene.coa_tools, 'surface_snap', text="Snap Vertices", icon="SNAP_ON")
            else:
                row2.prop(scene.coa_tools, 'surface_snap', text="Snap Vertices", icon="SNAP_OFF")

            col = layout.column(align=True)
            operator = col.operator("mesh.knife_tool", text="Knife")
            if "sprite" in obj.coa_tools:
                operator = col.operator("coa_tools.reproject_sprite_texture", text="Reproject Sprite")

### Custom template_list look
class COATOOLS_UL_AnimationCollections(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        ob = data
        slot = item
        col = layout.row(align=True)
        if item.name not in ["NO ACTION","Restpose"]:
            col.label(icon="ACTION")
            col.prop(item,"name",emboss=False,text="")
            col.prop(item,"export",text="")
        elif item.name == "NO ACTION":
            col.label(icon="RESTRICT_SELECT_ON")
            col.label(text=item.name)
        elif item.name == "Restpose":
            col.label(icon="ARMATURE_DATA")
            col.label(text=item.name)

        if context.scene.coa_tools.nla_mode == "NLA" and item.name not in ["NO ACTION","Restpose"]:
            col = layout.row(align=False)
            op = col.operator("coa_operator.create_nla_track",icon="NLA",text="")
            op.anim_collection_name = item.name

### Custom template_list look for event lists
class COATOOLS_UL_EventCollection(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        ob = data
        slot = item
        # col = layout.column(align=False)
        box = layout.box()
        col = box.column(align=False)

        row = col.row(align=False)
        # row.label(text="", icon="TIME")
        if item.collapsed:
            row.prop(item,"collapsed",emboss=False, text="", icon="TRIA_RIGHT")
        else:
            row.prop(item, "collapsed", emboss=False, text="", icon="TRIA_DOWN")
        row.prop(item, "frame", emboss=True, text="Frame")
        op = row.operator("coa_tools.remove_timeline_event", text="", icon="PANEL_CLOSE", emboss=False)
        op.index = index


        # row = col.row(align=True)
        if not item.collapsed:
            row = col.row(align=True)
            # row.alignment = "RIGHT"
            op = row.operator("coa_tools.add_event", icon="ADD", text="Add new Event", emboss=True)
            op.index = index
            for i, event in enumerate(item.event):
                row = col.row(align=True)
                row.prop(event, "type",text="")
                row.prop(event, "value",text="")
                op = row.operator("coa_tools.remove_event", icon="PANEL_CLOSE", text="", emboss=True)
                op.index = index
                op.event_index = i

######################################################################################################################################### Select Child Operator
class COATOOLS_OT_SelectChild(bpy.types.Operator):
    bl_idname = "coa_tools.select_child"
    bl_label = "Select Child"
    bl_description = "Select Outliner Item"

    ob_name: StringProperty()
    outliner_index: IntProperty(default=0)
    outliner_index_old = 0
    bone_name: StringProperty()

    def __init__(self):
        self.sprite_object = None

    mode: EnumProperty(items=(("object","object","object"),("bone","bone","bone")))
    armature = None

    def change_object_mode(self,context):
        obj = context.active_object
        if obj != None and self.ob_name != obj.name:
            if obj.mode == "EDIT" and obj.type == "MESH":
                bpy.ops.object.mode_set(mode="OBJECT")
            elif obj.mode == "EDIT" and obj.type == "ARMATURE":
                bpy.ops.object.mode_set(mode="POSE")


    def select_child(self,context,event):
        global last_obj
        self.change_object_mode(context)

        if self.mode == "object":
            ob = bpy.data.objects[self.ob_name]
            ob.select_set(True)
            context.view_layer.objects.active = ob
            if ob != None:
                last_obj = ob.name

            if not event.ctrl and not event.shift:
                for obj in context.scene.objects:
                    if obj != ob:
                        obj.select_set(False)

        elif self.mode == "bone":
            armature_ob = bpy.data.objects[self.ob_name]
            armature_ob.select_set(True)
            context.view_layer.objects.active = armature_ob
            armature = bpy.data.armatures[armature_ob.data.name]
            bpy.ops.object.mode_set(mode="POSE")
            for bone in armature.bones:
                bone.select = False
                bone.select_head = False
                bone.select_tail = False

            bone = armature.bones[self.bone_name]
            bone.select = not bone.select
            bone.select_tail = not bone.select_tail
            bone.select_head = not bone.select_head
            if bone.select == True:
                armature.bones.active = bone
            else:
                armature.bones.active = None

    def shift_select_child(self,context,event):
        self.change_object_mode(context)

        self.outliner_index_old = context.scene.coa_tools["outliner_index"]
        outliner = context.scene.coa_tools.outliner

        start_index = min(self.outliner_index_old, self.outliner_index)
        end_index = max(self.outliner_index_old, self.outliner_index)
        index_range = range(start_index, end_index+1)
        for item in outliner:
            if item.index in index_range:
                if item.object_type in ["MESH", "ARMATURE"]:
                    if item.entry_type in ["SPRITE","OBJECT"]:
                        bpy.data.objects[item.display_name].select_set(True)
                        if item.index == self.outliner_index:
                            context.view_layer.objects.active = bpy.data.objects[item.name]
                elif item.entry_type in ["BONE"]:
                    self.armature.data.bones[item.display_name].select = True
                    if item.index == self.outliner_index:
                        self.armature.data.bones.active = self.armature.data.bones[item.display_name]
    def invoke(self, context, event):
        self.sprite_object = functions.get_sprite_object(context.active_object)
        self.armature = functions.get_armature(self.sprite_object)
        if event.shift:
            self.shift_select_child(context, event)
        else:
            self.select_child(context, event)
        return{'FINISHED'}

class COATOOLS_PT_Collections(bpy.types.Panel):
    bl_idname = "COATOOLS_PT_collections"
    bl_label = "Cutout Animations"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "COA Tools"

    @classmethod
    def poll(cls, context):
        if not context.scene.coa_tools.deprecated_data_found:
            return context

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        scene = context.scene
        sprite_object = functions.get_sprite_object(obj)
        if sprite_object != None:
            # row = layout.row()
            # row.prop(sprite_object.coa_tools,"animation_loop",text="Wrap Animation Playback")

            row = layout.row()
            row.prop(scene.coa_tools,"nla_mode",expand=True)

            if scene.coa_tools.nla_mode == "NLA":
                row = layout.row(align=True)
                row.prop(scene.coa_tools,"frame_start")
                row.prop(scene.coa_tools,"frame_end")

            row = layout.row()
            box = row.box()
            box_col = box.column(align=True)
            box_label_row = box_col.split(factor=0.5, align=True)
            row1 = box_label_row.row()
            row2 = box_label_row.row()
            row2.alignment = "RIGHT"
            row1.label(text="Animation", icon="ACTION")
            row2.label(text="Export",icon="EXPORT")
            box_col.template_list("COATOOLS_UL_AnimationCollections","dummy",sprite_object.coa_tools, "anim_collections", sprite_object.coa_tools, "anim_collections_index",rows=2,maxrows=10,type='DEFAULT')
            col = row.column(align=True)
            col.operator("coa_tools.add_animation_collection",text="",icon="ADD")
            col.operator("coa_tools.remove_animation_collection",text="",icon="REMOVE")

            if len(sprite_object.coa_tools.anim_collections) > 2 and sprite_object.coa_tools.anim_collections_index > 1:
                col.operator("coa_tools.duplicate_animation_collection",text="",icon="COPY_ID")

            if not "-nonnormal" in context.screen.name:
                col.operator("coa_tools.toggle_animation_area",text="",icon="ACTION")

            if len(sprite_object.coa_tools.anim_collections) > 0 and sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index].action_collection:
                row = layout.row(align=True)
                item = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
                row.prop(item,"frame_end",text="Animation Length")


                # if get_addon_prefs(context).dragon_bones_export:
                row = layout.row(align=True)
                row.label(text="Timeline Events",icon="TIME")
                row = layout.row(align=False)
                row.template_list("COATOOLS_UL_EventCollection","dummy",item, "timeline_events", item, "event_index",rows=1,maxrows=10,type='DEFAULT')
                col = row.column(align=True)
                col.operator("coa_tools.add_timeline_event",text="",icon="ADD")

            row = layout.row(align=True)
            if context.scene.coa_tools.nla_mode == "ACTION":

                operator = row.operator("coa_tools.batch_render",text="Batch Render Animations",icon="RENDER_ANIMATION")
            else:
                operator = row.operator("render.render",text="Render Animation",icon="RENDER_ANIMATION")
                operator.animation = True

preview_collections = {}
