import bpy
from bpy.types import Menu
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
from .. functions import *
#from .. ui import preview_collections

preview_collections_pie = {}

class COATOOLS_MT_menu(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "COA Tools"
    bl_idname = "COATOOLS_MT_menu"
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        if context.area.type == "NLA_EDITOR ":
            return True

        if sprite_object != None:
            if (obj != None and ("sprite" in obj.coa_tools or "sprite_object" in obj.coa_tools) or ("coa_sprite" in obj or "sprite_object" in obj)) or (sprite_object != None and obj.type == "ARMATURE"):
                return True
    
    def draw(self, context):
        obj = context.active_object
        
        layout = self.layout
        pie = layout.menu_pie()
        if obj != None and context.area.type == "VIEW_3D":
            #pie.operator_enum("view3d.coa_pie_menu_options", "selected_mode")
            if obj.type == "MESH":
                pie.operator("coa_tools.select_frame_thumb",text="Select Frame",icon="IMAGE_RGB")
                pie.operator("wm.call_menu_pie", icon="KEYTYPE_MOVING_HOLD_VEC", text="Add Keyframe(s)").name = "COATOOLS_MT_keyframe_menu_add"
                pie.operator("coa_tools.edit_weights",text="Edit Weights",icon="MOD_VERTEX_WEIGHT")
                op = pie.operator("coa_tools.edit_mesh",text="Edit Mesh",icon="GREASEPENCIL")
                op.mode = "EDIT_MESH"
                pie.operator("coa_tools.quick_armature",text="Edit Armature",icon="ARMATURE_DATA")
                pie.operator("coa_tools.edit_shapekey",text="Edit Shapekey",icon="SHAPEKEY_DATA")
                pie.row()    
                pie.operator("wm.call_menu_pie", icon="HANDLETYPE_ALIGNED_VEC", text="Delete Keyframe(s)").name = "COATOOLS_MT_keyframe_menu_remove"
                
            elif obj.type == "ARMATURE":
                pie.operator("coa_tools.set_ik",text="Create IK Bone",icon="CONSTRAINT_BONE")
                pie.operator("wm.call_menu_pie", icon="KEYTYPE_MOVING_HOLD_VEC", text="Add Keyframe(s)").name = "COATOOLS_MT_keyframe_menu_add"
                pie.operator("coa_tools.draw_bone_shape",text="Draw Bone Shape",icon="BONE_DATA")
                pie.operator("coa_tools.quick_armature",text="Edit Armature",icon="ARMATURE_DATA")
                pie.operator("coa_tools.set_stretch_bone",text="Create Stretch Bone",icon="CONSTRAINT_BONE")
                pie.operator("wm.call_menu_pie", icon="HANDLETYPE_ALIGNED_VEC", text="Delete Keyframe(s)").name = "COATOOLS_MT_keyframe_menu_remove"
            elif obj.type == "EMPTY":
                pie.operator("import.coa_import_sprites",text="Import Sprites",icon="FILEBROWSER")
                if get_addon_prefs(context).dragon_bones_export:
                    pie.operator("coa_tools.export_dragon_bones",text="Export Dragonbones",icon_value=db_icon.icon_id)
                else:
                    pie.row()    
                pie.operator("wm.coa_create_ortho_cam",text="Create Ortho Camera",icon="CAMERA_DATA")
                pie.operator("coa_tools.batch_render",text="Batch Render Animations",icon="CLIP")

class COATOOLS_MT_keyframe_menu_01(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "COA Tools"
    bl_idname = "COATOOLS_MT_keyframe_menu_01"
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        if (obj != None and "coa_sprite" in obj) or (sprite_object != None and obj.type == "ARMATURE"):
            return True
    
    def draw(self, context):
        obj = context.active_object
        
        layout = self.layout
        pie = layout.menu_pie()
        if obj != None:
            pie.operator("wm.call_menu_pie", icon="KEYTYPE_MOVING_HOLD_VEC", text="Add Keyframe(s)").name = "view3d.coa_pie_keyframe_menu_add"
            pie.operator("wm.call_menu_pie", icon="HANDLETYPE_ALIGNED_VEC", text="Delete Keyframe(s)").name = "view3d.coa_pie_keyframe_menu_remove"

class COATOOLS_MT_keyframe_menu_add(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "COA Add Keyframe"
    bl_idname = "COATOOLS_MT_keyframe_menu_add"
    
    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        add_remove_keyframe(pie,True)
        
class COATOOLS_MT_keyframe_menu_remove(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "COA Remove Keyframe"
    bl_idname = "COATOOLS_MT_keyframe_menu_remove"
    
    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        add_remove_keyframe(pie,False)


def add_remove_keyframe(pie, add):
    context = bpy.context
    obj = context.active_object
    if obj.type == "MESH":
        op = pie.operator("coa_tools.add_keyframe", text="Slot Index", icon="IMAGE_RGB")
        op.prop_name = "coa_tools.slot_index"
        op.add_keyframe = add
        op.default_interpolation = "CONSTANT"

        op = pie.operator("coa_tools.add_keyframe", text="Sprite Alpha", icon="RESTRICT_VIEW_OFF")
        op.prop_name = "coa_tools.alpha"
        op.add_keyframe = add
        op.default_interpolation = "BEZIER"

        op = pie.operator("coa_tools.add_keyframe", text="Modulate Color", icon="COLOR")
        op.prop_name = "coa_tools.modulate_color"
        op.add_keyframe = add
        op.default_interpolation = "BEZIER"

        op = pie.operator("coa_tools.add_keyframe", text="Z Value", icon="IMAGE_ZDEPTH")
        op.prop_name = "coa_tools.z_value"
        op.add_keyframe = add
        op.default_interpolation = "CONSTANT"

    elif obj.type == "ARMATURE":
        bone = context.active_pose_bone
        op = pie.operator("coa_tools.add_keyframe", text="Location")
        op.prop_name = "location"
        op.add_keyframe = add
        op.default_interpolation = "BEZIER"

        op = pie.operator("coa_tools.add_keyframe", text="Scale")
        op.prop_name = "scale"
        op.add_keyframe = add
        op.default_interpolation = "BEZIER"

        op = pie.operator("coa_tools.add_keyframe", text="Rotation")
        op.prop_name = "rotation"
        op.add_keyframe = add
        op.default_interpolation = "BEZIER"

        op = pie.operator("coa_tools.add_keyframe", text="Location Rotation Scale", icon="MOD_ARMATURE")
        op.prop_name = "LocRotScale"
        op.add_keyframe = add
        op.default_interpolation = "BEZIER"
