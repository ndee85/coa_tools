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

bl_info = {
    "name": "COA Tools",
    "description": "This Addon provides a Toolset for a 2D Animation Workflow.",
    "author": "Andreas Esau",
    "version": (2, 0, 0),
    "blender": (2, 80, 0),
    "location": "View 3D > Tools > Cutout Animation Tools",
    "warning": "",
    "wiki_url": "https://github.com/ndee85/coa_tools/wiki",
    "tracker_url": "https://github.com/ndee85/coa_tools/issues",
    "category": "Ndee Tools" }


import bpy
import os
import shutil
import tempfile
from bpy.app.handlers import persistent

from . import addon_updater_ops

# load and reload submodules
##################################

from . import properties as props

from . import ui as user_interface
from . ui import preview_collections
from . import outliner
from . operators.pie_menu import preview_collections_pie
from . functions import *

from . operators import create_sprite_object
from . operators import help_display

from . operators import advanced_settings
from . operators import animation_handling
from . operators import create_ortho_cam
from . operators import create_spritesheet_preview
from . operators import donations
from . operators import draw_bone_shape
from . operators import edit_armature
from . operators import edit_mesh
from . operators import edit_shapekey
from . operators import edit_weights
from . operators import import_sprites
from . operators import material_converter
from . operators import pie_menu
from . operators import slot_handling
from . operators import toggle_animation_area
from . operators import view_sprites
from . operators import version_converter
from . operators import change_alpha_mode

from . operators.exporter import export_dragonbones
from . operators.exporter import export_creature

# register
################################## 

import traceback



class COAToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_donate_icon: bpy.props.BoolProperty(name="Show Donate Icon",default=False)
    sprite_import_export_scale: bpy.props.FloatProperty(name="Sprite import/export scale",default=0.01)

    auto_check_update: bpy.props.BoolProperty(
    name = "Auto-check for Update",
    description = "If enabled, auto-check for updates using an interval",
    default = True,
    )
    updater_intrval_months: bpy.props.IntProperty(
    name='Months',
    description = "Number of months between checking for updates",
    default=0,
    min=0
    )
    updater_intrval_days: bpy.props.IntProperty(
    name='Days',
    description = "Number of days between checking for updates",
    default=1,
    min=0,
    )
    updater_intrval_hours: bpy.props.IntProperty(
    name='Hours',
    description = "Number of hours between checking for updates",
    default=0,
    min=0,
    max=23
    )
    updater_intrval_minutes: bpy.props.IntProperty(
    name='Minutes',
    description = "Number of minutes between checking for updates",
    default=0,
    min=0,
    max=59
    )

    def draw(self, context):
        layout = self.layout
        # layout.prop(self, "show_donate_icon")
        layout.prop(self, "sprite_import_export_scale")

        addon_updater_ops.update_settings_ui(self, context)


classes = (
    COAToolsPreferences,
    # outliner
    outliner.COAOutliner,
    outliner.COATOOLS_UL_Outliner,

    #properties
    props.UVData,
    props.SlotData,
    props.Event,
    props.TimelineEvent,
    props.AnimationCollections,
    props.ObjectProperties,
    props.SceneProperties,
    props.MeshProperties,
    props.BoneProperties,
    props.WindowManagerProperties,

    #operator
    create_sprite_object.COATOOLS_OT_CreateSpriteObject,
    create_sprite_object.COATOOLS_OT_DefineSpriteObject,
    import_sprites.JsonImportData,
    import_sprites.COATOOLS_OT_CreateMaterialGroup,
    import_sprites.COATOOLS_OT_ImportSprite,
    import_sprites.COATOOLS_OT_ImportSprites,
    import_sprites.COATOOLS_OT_LoadJsonData,
    import_sprites.COATOOLS_UL_JsonImport,
    import_sprites.COATOOLS_OT_ReImportSprite,

    user_interface.COATOOLS_OT_ChangeShadingMode,
    user_interface.COATOOLS_PT_Info,
    user_interface.COATOOLS_PT_ObjectProperties,
    user_interface.COATOOLS_PT_Tools,
    user_interface.COATOOLS_UL_AnimationCollections,
    user_interface.COATOOLS_UL_EventCollection,
    user_interface.COATOOLS_OT_SelectChild,
    user_interface.COATOOLS_PT_Collections,

    view_sprites.COATOOLS_OT_ChangeZOrdering,
    view_sprites.COATOOLS_OT_ViewSprite,

    advanced_settings.COATOOLS_OT_AdvancedSettings,

    edit_mesh.COATOOLS_OT_ReprojectSpriteTexture,
    edit_mesh.COATOOLS_OT_GenerateMeshFromEdgesAndVerts,
    edit_mesh.COATOOLS_OT_DrawContour,
    edit_mesh.COATOOLS_OT_PickEdgeLength,

    edit_armature.COATOOLS_OT_TooglePoseMode,
    edit_armature.COATOOLS_OT_BindMeshToBones,
    edit_armature.COATOOLS_OT_QuickArmature,
    edit_armature.COATOOLS_OT_SetStretchBone,
    edit_armature.COATOOLS_OT_RemoveIK,
    edit_armature.COATOOLS_OT_SetIK,
    edit_armature.COATOOLS_OT_CreateStretchIK,
    edit_armature.COATOOLS_OT_RemoveStretchIK,

    edit_shapekey.COATOOLS_OT_LeaveSculptmode,
    edit_shapekey.COATOOLS_OT_ShapekeyAdd,
    edit_shapekey.COATOOLS_OT_ShapekeyRemove,
    edit_shapekey.COATOOLS_OT_ShapekeyRename,
    edit_shapekey.COATOOLS_OT_EditShapekeyMode,

    edit_weights.COATOOLS_OT_EditWeights,

    slot_handling.COATOOLS_OT_ExtractSlots,
    slot_handling.COATOOLS_OT_CreateSlotObject,
    slot_handling.COATOOLS_OT_MoveSlotItem,
    slot_handling.COATOOLS_OT_RemoveFromSlot,

    animation_handling.COATOOLS_OT_AddKeyframe,
    animation_handling.COATOOLS_OT_DuplicateAnimationCollection,
    animation_handling.COATOOLS_OT_AddAnimationCollection,
    animation_handling.COATOOLS_OT_RemoveAnimationCollection,
    animation_handling.COATOOLS_OT_CreateNlaTrack,
    animation_handling.COATOOLS_OT_BatchRender,
    animation_handling.COATOOLS_OT_AddEvent,
    animation_handling.COATOOLS_OT_RemoveEvent,
    animation_handling.COATOOLS_OT_AddTimelineEvent,
    animation_handling.COATOOLS_OT_RemoveTimelineEvent,

    create_ortho_cam.COATOOLS_OT_CreateOrtpographicCamera,
    create_ortho_cam.COATOOLS_OT_AlignCamera,

    create_spritesheet_preview.COATOOLS_OT_SelectFrameThumb,

    help_display.COATOOLS_OT_ShowHelp,

    draw_bone_shape.COATOOLS_OT_DrawBoneShape,

    pie_menu.COATOOLS_MT_menu,
    pie_menu.COATOOLS_MT_keyframe_menu_01,
    pie_menu.COATOOLS_MT_keyframe_menu_add,
    pie_menu.COATOOLS_MT_keyframe_menu_remove,

    toggle_animation_area.COATOOLS_OT_ToggleAnimationArea,
    version_converter.COATOOLS_OT_VersionConverter,

    change_alpha_mode.COATOOLS_OT_ChangeAlphaMode,
    change_alpha_mode.COATOOLS_OT_ChangeTextureInterpolationMode,

    # exporter
    export_dragonbones.COATOOLS_OT_DragonBonesExport,
    export_dragonbones.COATOOLS_PT_ExportPanel,
    export_creature.COATOOLS_OT_CreatureExport,

)

addon_keymaps = []
def register_keymaps():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new('view3d.move', 'MIDDLEMOUSE', 'PRESS')
        kmi.active = False

    addon = bpy.context.window_manager.keyconfigs.addon
    km = addon.keymaps.new(name="3D View", space_type="VIEW_3D")
    # insert keymap items here
    kmi = km.keymap_items.new("wm.call_menu_pie", type = "F", value = "PRESS")
    kmi.properties.name = "COATOOLS_MT_menu"
    addon_keymaps.append(km)

def unregister_keymaps():
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        for kmi in km.keymap_items:
            km.keymap_items.remove(kmi)
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()


def register():
    addon_updater_ops.register(bl_info)
    copy_icons()

    # register classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # register tools
    # bpy.utils.register_tool(edit_mesh.COATOOLS_TO_DrawPolygon, after={"builtin.cursor"}, separator=True, group=True)

    # register props and keymap
    props.register()
    register_keymaps()

    # create handler
    bpy.app.handlers.depsgraph_update_pre.append(outliner.create_outliner_items)
    bpy.app.handlers.frame_change_post.append(update_properties)
    bpy.app.handlers.depsgraph_update_post.append(update_properties)
    bpy.app.handlers.load_post.append(check_view_2D_3D)
    bpy.app.handlers.load_post.append(check_for_deprecated_data)
    bpy.app.handlers.load_post.append(set_shading)


def unregister():
    addon_updater_ops.unregister()

    # unregister classes
    for cls in classes:
        bpy.utils.unregister_class(cls)

    # unregister tools
    bpy.utils.unregister_tool(edit_mesh.COATOOLS_TO_DrawPolygon)

    # unregisters props and keymap
    props.unregister()
    unregister_keymaps()

    # delete handler
    bpy.app.handlers.depsgraph_update_pre.remove(outliner.create_outliner_items)
    bpy.app.handlers.frame_change_post.remove(update_properties)
    bpy.app.handlers.depsgraph_update_post.remove(update_properties)
    bpy.app.handlers.load_post.remove(check_view_2D_3D)
    bpy.app.handlers.load_post.remove(check_for_deprecated_data)


@persistent
def check_for_deprecated_data(dummy):
    for obj in bpy.data.objects:
        if "sprite_object" in obj:
            bpy.context.scene.coa_tools.deprecated_data_found = True

@persistent
def check_view_2D_3D(dummy):
    context = bpy.context
    if context != None:
        scene = context.scene
        if scene != None:
            if scene.coa_tools.view == "2D":
                set_middle_mouse_move(True)
            elif scene.coa_tools.view == "3D":
                set_middle_mouse_move(False)


@persistent
def set_shading(dummy):
    bpy.context.scene.eevee.use_taa_reprojection = False
    for obj in bpy.data.objects:
        if "sprite_object" in obj.coa_tools:
            for screen in bpy.data.screens:
                for area in screen.areas:
                    if area.type == "VIEW_3D":
                        area.spaces[0].shading.type = "SOLID"
                        area.spaces[0].shading.light = "FLAT"
            break
    bpy.ops.coa_tools.updater_check_now()

@persistent
def update_properties(scene, depsgraph):
    context = bpy.context
    for obj in bpy.data.objects:
        obj_eval = obj.evaluated_get(depsgraph)
        
        if obj_eval.coa_tools.slot_index != obj_eval.coa_tools.slot_index_last:
            change_slot_mesh_data(bpy.context, obj, obj_eval)
            obj.coa_tools.slot_index_last = obj_eval.coa_tools.slot_index

        if obj_eval.coa_tools.alpha != obj_eval.coa_tools.alpha_last:
            set_alpha(obj, context, obj_eval.coa_tools.alpha)
            obj.coa_tools.alpha_last = obj_eval.coa_tools.alpha

        if obj_eval.coa_tools.modulate_color != obj_eval.coa_tools.modulate_color_last:
            set_modulate_color(obj, context, obj_eval.coa_tools.modulate_color)
            obj.coa_tools.modulate_color_last = obj_eval.coa_tools.modulate_color

        if obj_eval.coa_tools.z_value != obj_eval.coa_tools.z_value_last:
            set_z_value(context, obj, obj_eval.coa_tools.z_value)
            obj.coa_tools.z_value_last = obj_eval.coa_tools.z_value



def copy_icons():
    version = str(bpy.app.version[0]) + "." + str(bpy.app.version[1])

    icons = [
        "coa_tools.draw_polygon.dat",
        "coa_tools.draw_bone.dat",
        ]

    for icon_name in icons:
        icon_path = os.path.join(bpy.utils.user_resource("SCRIPTS", "addons"), "coa_tools", "icons", icon_name)
        b_icon_path = os.path.join(os.path.dirname(bpy.app.binary_path), version, "datafiles", "icons", icon_name)

        if os.path.isfile(b_icon_path):
            try:
                os.remove(b_icon_path)
            except IOError as e:
                print("Unable to delete file. %s" % e)

        dir_path = os.path.dirname(b_icon_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        try:
            shutil.copyfile(icon_path, b_icon_path)
        except IOError as e:
            print("Unable to copy file. %s" % e)
