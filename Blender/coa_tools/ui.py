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
from . functions import *
#from . import preview_collections

bone_layers = []
armature_mode = None
armature_select = False
tmp_active_object = None


class UVData(bpy.types.PropertyGroup):
    uv = FloatVectorProperty(default=(0,0),size=2)

class SlotData(bpy.types.PropertyGroup):
    def change_slot_mesh(self,context):
        obj = self.id_data
        self["active"] = True
        if self.active:
            obj.coa_slot_index = self.index
            hide_base_sprite(obj)
            for slot in obj.coa_slot:
                if slot != self:
                    slot["active"] = False
                    
    name = StringProperty()
    active = BoolProperty(update=change_slot_mesh)
    index = IntProperty()

class Event(bpy.types.PropertyGroup):
    def change_event_order(self,context):
        events = self.id_data.coa_anim_collections[self.id_data.coa_anim_collections_index].event
        for i,event in enumerate(events):
            if i+1 < len(events):
                if events[i].frame == events[i+1].frame:
                    events.remove(i+1)
                if events[i].frame > events[i+1].frame:
                    events.move(i,i+1)
    
    frame = IntProperty(default=0,min=0,update=change_event_order)
    event = StringProperty(default="")
    sound = StringProperty(default="")
    action = StringProperty(default="")

class AnimationCollections(bpy.types.PropertyGroup):
    def set_frame_start(self,context):
        bpy.context.scene.frame_start = self.frame_start
    def set_frame_end(self,context):
        bpy.context.scene.frame_end = self.frame_end
    
    def check_name(self,context):
        sprite_object = get_sprite_object(context.active_object)
        
        if self.name_old != "" and self.name_change_to != self.name:
            name_array = []
            for item in sprite_object.coa_anim_collections:
                name_array.append(item.name_old)
            self.name_change_to = check_name(name_array,self.name)
            self.name = self.name_change_to 
        
        for child in get_children(context,sprite_object,ob_list=[]):
            action_name = self.name_old + "_" + child.name
            action_name_new = self.name + "_" + child.name
            if action_name in bpy.data.actions:
                action = bpy.data.actions[action_name]
                action.name = action_name_new
        self.name_old = self.name
    
    name = StringProperty(update=check_name)
    name_change_to = StringProperty()
    name_old = StringProperty()
    action_collection = BoolProperty(default=False)
    frame_start = IntProperty(default=0 ,update=set_frame_start)
    frame_end = IntProperty(default=250 ,update=set_frame_end)
    event = CollectionProperty(type=Event)
    event_index = IntProperty(default=-1,max=-1)
        

class CutoutAnimationInfo(bpy.types.Panel):
    bl_idname = "cutout_animation_social"
    bl_label = "Cutout Animation Social"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Cutout Animation"
    
    @classmethod
    def poll(cls, context):
        if get_addon_prefs(context).show_donate_icon:
            return context
    
    def draw(self, context):
        
        
        layout = self.layout
        
        row = layout.row()
        row.alignment = "CENTER"
        
        pcoll = preview_collections["main"]
        donate_icon = pcoll["donate_icon"]
        twitter_icon = pcoll["twitter_icon"]
        row.operator("coa_operator.coa_donate",text="Show Your Love",icon_value=donate_icon.icon_id,emboss=True)
        row = layout.row()
        row.alignment = "CENTER"
        row.scale_x = 1.75
        op = row.operator("coa_operator.coa_tweet",text="Tweet",icon_value=twitter_icon.icon_id,emboss=True)
        op.link = "https://www.youtube.com/ndee85"
        op.text = "Check out CutoutAnimation Tools Addon for Blender by Andreas Esau."
        op.hashtags = "b3d,coatools"
        op.via = "ndee85"


def enum_sprite_previews(self, context):
    """EnumProperty callback"""
    enum_items = []
    
    if context is None:
        return enum_items

    # Get the preview collection (defined in register func).
    coa_pcoll = preview_collections["coa_thumbs"]
    
    #thumb_dir_path = bpy.utils.user_resource("DATAFILES","coa_thumbs")
    thumb_dir_path = os.path.join(context.user_preferences.filepaths.temporary_directory,"coa_thumbs")
    
    if os.path.exists(thumb_dir_path):
        # Scan the directory for png files
        image_paths = []
        for fn in os.listdir(thumb_dir_path):
            if fn.lower().endswith(".png") and self.name in fn:
                image_paths.append(fn)      
        for i, name in enumerate(image_paths):
            if i < self.coa_tiles_x * self.coa_tiles_y:
                filepath = os.path.join(thumb_dir_path, name)

                if name in coa_pcoll:
                    thumb = coa_pcoll[name]
                else:    
                    thumb = coa_pcoll.load(name, filepath, 'IMAGE')
                enum_items.append((str(i), name, "", thumb.icon_id, i))
 
    return enum_items
    
class CutoutAnimationObjectProperties(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Object Properties"
    bl_category = "Cutout Animation"
    
    @classmethod
    def poll(cls, context):
        return (context.active_object)
    
    def hide_bone(self,context):
        self.hide = self.coa_hide
    
    def hide_select_bone(self,context):
        self.hide_select = self.coa_hide_select
    
    def hide(self,context):
        if self.coa_hide:
            if context.scene.objects.active == self:
                context.scene.objects.active = self.parent
        self.hide = self.coa_hide
    def hide_select(self,context):
        if self.coa_hide_select:
            self.select = False
            if context.scene.objects.active == self:
                context.scene.objects.active = self.parent
        self.hide_select = self.coa_hide_select
    
    def update_uv(self,context):
        self.coa_sprite_frame_last = -1
        if self.coa_sprite_frame >= (self.coa_tiles_x * self.coa_tiles_y):
            self.coa_sprite_frame = (self.coa_tiles_x * self.coa_tiles_y) - 1
        update_uv(context,context.active_object)
    
        
    def change_tilesize(self,context):
        obj = context.active_object
        frame = self.coa_sprite_frame
        self.coa_sprite_frame = 0

        update_verts(context,obj)
        update_uv(context,obj)
        
        self.coa_sprite_frame = frame
        self.coa_tiles_changed = True
        
    
    def set_z_value(self,context):
        #obj = context.active_object
        
        if context.scene.objects.active == self:
            for obj in bpy.context.selected_objects:
                if obj.type == "MESH":
                    if obj != self:
                        obj.coa_z_value = self.coa_z_value
                    set_z_value(context,obj,self.coa_z_value)
                
            
    def set_alpha(self,context):
        if context.scene.objects.active == self:
            for obj in bpy.context.selected_objects:
                if obj.type == "MESH":
                    if obj != self:
                        obj.coa_alpha = self.coa_alpha
                    set_alpha(obj,context,self.coa_alpha)
    
    def set_modulate_color(self,context):
        if context.scene.objects.active == self:
            for obj in bpy.context.selected_objects:
                if obj.type == "MESH":
                    if obj != self:
                        obj.coa_modulate_color = self.coa_modulate_color
                    set_modulate_color(obj,context,self.coa_modulate_color)
            
    def set_sprite_frame(self,context):
        self.coa_sprite_frame_last = -1
        self.coa_sprite_frame = int(self.coa_sprite_frame_previews)
        if context.scene.tool_settings.use_keyframe_insert_auto:
            bpy.ops.my_operator.add_keyframe(prop_name="coa_sprite_frame",interpolation="CONSTANT")
    
    
    def exit_edit_weights(self,context):
        if not self.coa_edit_weights:
            obj = context.active_object
            if obj != None and obj.mode == "WEIGHT_PAINT":
                bpy.ops.object.mode_set(mode="OBJECT")
    
    def hide_base_sprite(self,context):
        #hide_base_sprite(self)
        hide_base_sprite(context.active_object)
    
    def change_slot_mesh(self,context):
        self.coa_slot_index_last = -1
        self.coa_slot_index_last = self.coa_slot_index
        change_slot_mesh_data(context,self)
    
    def change_edit_mode(self,context):
        if self.coa_edit_mesh == False:
            bpy.ops.object.mode_set(mode="OBJECT")
            set_local_view(False)
    
    def update_filter(self,context):
        pass
        
    bpy.types.Object.coa_dimensions_old = FloatVectorProperty()
    bpy.types.Object.coa_sprite_dimension = FloatVectorProperty()
    bpy.types.Object.coa_tiles_x = IntProperty(description="X Tileset",default = 1,min=1,update=change_tilesize)
    bpy.types.Object.coa_tiles_y = IntProperty(description="Y Tileset",default = 1,min=1,update=change_tilesize)
    bpy.types.Object.coa_sprite_frame = IntProperty(description="Frame",default = 0,min=0,update=update_uv)
    bpy.types.Object.coa_sprite_frame_last = IntProperty(description="Frame")
    bpy.types.Object.coa_z_value = IntProperty(description="Z Depth",default=0,update=set_z_value)
    bpy.types.Object.coa_z_value_last = IntProperty(default=0)
    bpy.types.Object.coa_alpha = FloatProperty(default=1.0,min=0.0,max=1.0,update=set_alpha)
    bpy.types.Object.coa_alpha_last = FloatProperty(default=1.0,min=0.0,max=1.0)
    bpy.types.Object.coa_show_bones = BoolProperty()
    bpy.types.Object.coa_filter_names = StringProperty(update=update_filter,options={'TEXTEDIT_UPDATE'})
    bpy.types.Object.coa_favorite = BoolProperty()
    bpy.types.Object.coa_hide_base_sprite = BoolProperty(default=False,update=hide_base_sprite)
    bpy.types.Mesh.coa_hide_base_sprite = BoolProperty(default=False,update=hide_base_sprite)
    bpy.types.Object.coa_animation_loop = BoolProperty(default=False,description="Sets the Timeline frame to 0 when it reaches the end of the animation. Also works for changing frame with cursor keys.")
    bpy.types.Bone.coa_favorite = BoolProperty()
    bpy.types.Object.coa_edit_weights = BoolProperty(default=False,update=exit_edit_weights)
    bpy.types.Object.coa_edit_armature = BoolProperty(default=False)
    bpy.types.Object.coa_edit_mesh = BoolProperty(default=False,update=change_edit_mode)
    bpy.types.Object.coa_hide = BoolProperty(default=False,update=hide)
    bpy.types.Object.coa_hide_select = BoolProperty(default=False,update=hide_select)
    bpy.types.Object.coa_data_path = StringProperty()
    bpy.types.Object.coa_show_children = BoolProperty(default=True)
    bpy.types.Bone.coa_draw_bone = BoolProperty(default=False)
    bpy.types.Bone.coa_z_value = IntProperty(description="Z Depth",default=0)
    bpy.types.Bone.coa_data_path = StringProperty()
    bpy.types.Bone.coa_hide_select = BoolProperty(default=False, update=hide_select_bone)
    bpy.types.Bone.coa_hide = BoolProperty(default=False,update=hide_bone)
    bpy.types.Object.coa_show_export_box = BoolProperty()
    bpy.types.Object.coa_sprite_frame_previews = EnumProperty(items = enum_sprite_previews,update=set_sprite_frame)
    bpy.types.Object.coa_tiles_changed = BoolProperty(default=False)
    bpy.types.Object.coa_sprite_updated = BoolProperty(default=False)
    bpy.types.Object.coa_modulate_color = FloatVectorProperty(name="Modulate Color",description="Modulate color for sprites. This will tint your sprite with given color.",default=(1.0,1.0,1.0),min=0.0,max=1.0,soft_min=0.0,soft_max=1.0,size=3,subtype="COLOR",update=set_modulate_color)
    bpy.types.Object.coa_modulate_color_last = FloatVectorProperty(default=(1.0,1.0,1.0),min=0.0,max=1.0,soft_min=0.0,soft_max=1.0,size=3,subtype="COLOR")
    bpy.types.Object.coa_type = EnumProperty(name="Object Type",default="MESH",items=(("SPRITE","Sprite","Sprite"),("MESH","Mesh","Mesh"),("SLOT","Slot","Slot")))
    bpy.types.Object.coa_slot_index = bpy.props.IntProperty(default=0,update=change_slot_mesh,min=0)
    bpy.types.Object.coa_slot_index_last = bpy.props.IntProperty()
    bpy.types.Object.coa_slot_reset_index = bpy.props.IntProperty(default=0,min=0)
    bpy.types.Object.coa_slot_show = bpy.props.BoolProperty(default=False)
    
    bpy.types.WindowManager.coa_running_modal = BoolProperty(default=False)
                
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        scene = context.scene
        
        
        
        #if len(sprite_object.children) > 0:
        display_children(self,context,obj)
#        if sprite_object != None:
#        else:
#            display_children(self,context,obj)
        
        if sprite_object != None:
            
            row = layout.row(align=True)
            row.label(text="",icon="OBJECT_DATA")
            row.separator()
            row.prop(obj,"name",text="")
            if obj.type == "ARMATURE":
                row = layout.row(align=True)
                if context.active_bone != None:
                    row.label(text="", icon="BONE_DATA")
                    row.separator()
                    row.prop(context.active_bone,'name',text="")
                    if context.active_object.mode != "EDIT" and get_addon_prefs(context).json_export:
                        box = layout.box()
                        row = box.row(align=True)
                        if sprite_object.coa_show_export_box:
                            row.prop(sprite_object,"coa_show_export_box",text="Json Export Properties",icon="TRIA_DOWN",emboss=False)
                            row = box.row(align=True)
                            row.prop(context.active_bone,"coa_draw_bone",text="Draw Bone on export")
                            row = box.row(align=True)
                        else:
                            row.prop(sprite_object,"coa_show_export_box",text="Json Export Properties",icon="TRIA_RIGHT",emboss=False)    
            
            if obj != None and obj.type == "MESH" and obj.mode == "OBJECT":
                row = layout.row(align=True)
                row.label(text="Sprite Properties:")
                
            if obj != None and obj.type == "MESH" and "coa_sprite" in obj and "coa_base_sprite" in obj.modifiers:
                row = layout.row(align=True)
                #row.prop(obj,'coa_hide_base_sprite',text="Hide Base Sprite")
                row.prop(obj.data,'coa_hide_base_sprite',text="Hide Base Sprite")
            
            if obj != None and obj.type == "MESH" and obj.mode == "OBJECT":
                
                row = layout.row(align=True)
                text = str(obj.coa_tiles_x * obj.coa_tiles_y) + " Frame(s) total"
                row.label(text=text)
                    
                if obj.coa_type == "MESH":    
                    row = layout.row(align=True)
                    row.prop(obj,'coa_tiles_x',text="Tiles X")
                    row.prop(obj,'coa_tiles_y',text="Tiles Y")
                    
                    row = layout.row(align=True)
                    row.prop(obj,'coa_sprite_frame',text="Frame Index",icon="UV_FACESEL")
                
                    if obj.coa_tiles_x * obj.coa_tiles_y > 1:
                        op = row.operator("my_operator.select_frame_thumb",text="",icon="IMAGE_COL")
                        
                        op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                        op.prop_name = "coa_sprite_frame"
                        op.add_keyframe = True
                        op.default_interpolation = "CONSTANT"
                        op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                        op.prop_name = "coa_sprite_frame"
                        op.add_keyframe = False
                        #row.template_icon_view(obj, "coa_sprite_frame_previews")
                else:
                    row = layout.row(align=True)
                    row.prop(obj,'coa_slot_index',text="Slot Index") 
                    
                    op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                    op.prop_name = "coa_slot_index"
                    op.add_keyframe = True
                    op.default_interpolation = "CONSTANT"
                    op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                    op.prop_name = "coa_slot_index"
                    op.add_keyframe = False   
            
            if obj != None and obj.type == "MESH" and obj.mode == "OBJECT":
                
                    
                
                row = layout.row(align=True)
                row.prop(obj,'coa_z_value',text="Z Depth")
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                op.prop_name = "coa_z_value"
                op.add_keyframe = True
                op.default_interpolation = "CONSTANT"
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                op.prop_name = "coa_z_value"
                op.add_keyframe = False
                
                row = layout.row(align=True)
                row.prop(obj,'coa_alpha',text="Alpha",icon="TEXTURE")
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                op.prop_name = "coa_alpha"
                op.add_keyframe = True
                op.default_interpolation = "BEZIER"
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                op.prop_name = "coa_alpha"
                op.add_keyframe = False
                
                row = layout.row(align=True)
                row.prop(obj,'coa_modulate_color',text="")
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                op.prop_name = "coa_modulate_color"
                op.add_keyframe = True
                op.default_interpolation = "LINEAR"
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                op.prop_name = "coa_modulate_color"
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
class CutoutAnimationTools(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Cutout Tools"
    bl_category = "Cutout Animation"
    
    def snapping(self,context):
        if bpy.context.scene.coa_surface_snap:
            bpy.context.scene.tool_settings.use_snap = True
            bpy.context.scene.tool_settings.snap_element = 'FACE'
        else:
            bpy.context.scene.tool_settings.use_snap = False
    
    def lock_view(self,context):
        screen = context.screen
        if "-nonnormal" in self.name:
            bpy.data.screens[context.screen.name.split("-nonnormal")[0]].coa_view = self.coa_view
        if screen.coa_view == "3D":
            set_middle_mouse_move(False)
            set_view(screen,"3D")
        elif screen.coa_view == "2D":
            set_middle_mouse_move(True)
            set_view(screen,"2D")
    
    def update_stroke_distance(self,context):
        mult = bpy.context.space_data.region_3d.view_distance*.05
        if self.coa_distance_constraint:
            context.scene.coa_distance /= mult
        else:
            context.scene.coa_distance *= mult
    
    bpy.types.Scene.coa_distance = FloatProperty(description="Set the asset distance for each Paint Stroke",default = 1.0,min=-.0, max=30.0)
    bpy.types.Scene.coa_detail = FloatProperty(description="Detail",default = .3,min=0,max=1.0)
    bpy.types.Scene.coa_snap_distance = FloatProperty(description="Snap Distance",default = 0.01,min=0)
    bpy.types.Scene.coa_surface_snap = BoolProperty(default=False,description="Snap Vertices on Surface",update=snapping)
    bpy.types.Scene.coa_automerge = BoolProperty(default=False)
    bpy.types.Scene.coa_distance_constraint = BoolProperty(default=False,description="Constraint Distance to Viewport", update=update_stroke_distance)
    bpy.types.Scene.coa_lock_to_bounds = BoolProperty(default=True,description="Lock Cursor to Object Bounds")
    bpy.types.Scene.coa_frame_last = IntProperty(description="Stores last frame Number",default=0)
    
    bpy.types.Screen.coa_view = EnumProperty(default="3D",items=(("3D","3D View","3D","MESH_CUBE",0),("2D","2D View","2D","MESH_PLANE",1)),update=lock_view)
    bpy.types.WindowManager.coa_show_help = BoolProperty(default=False,description="Hide Help")
    
    
    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        scene = context.scene    
        screen = context.screen
        
        pcoll = preview_collections["main"]
        db_icon = pcoll["db_icon"]
        
        row = layout.row(align=True)
        row.prop(screen,"coa_view",expand=True)
        if not wm.coa_show_help:
            row.operator("coa_tools.show_help",text="",icon="QUESTION")
        else:
            row.prop(wm,"coa_show_help",text="",icon="QUESTION")    
        
        if context.active_object == None or (context.active_object != None):
            if obj != None and obj.mode in ["OBJECT","POSE"]:
                row = layout.row(align=True)
                row.label(text="General Operator:")
            
                row = layout.row(align=True)
                op = row.operator("wm.coa_create_ortho_cam",text="Create Camera", icon="OUTLINER_DATA_CAMERA")
                op.create = True
        if obj != None and obj.type == "CAMERA":    
            row = layout.row(align=True)
            op = row.operator("wm.coa_create_ortho_cam",text="Reset Camera Resolution",icon="OUTLINER_DATA_CAMERA")
            op.create = False
            
#            row = layout.row(align=True)
#            row.operator("coa_tools.align_camera",text="Align 2D Camera",icon="ALIGN")
        
        if context.active_object == None or (context.active_object != None and context.active_object.mode not in ["EDIT","WEIGHT_PAINT"]):
            row = layout.row(align=True)
            row.operator("wm.coa_create_sprite_object",text="Create new Sprite Object",icon="TEXTURE_DATA")
        
        if context.active_object != None and get_sprite_object(context.active_object) != None:
            if sprite_object.coa_edit_weights == False:
                if context.active_object.mode != "EDIT":
                    row = layout.row(align=True)
                    row.operator("import.coa_import_sprites",text="Import Sprites",icon="IMASEL")
                    if context.active_object.type == "MESH":
                        row.operator("import.coa_reimport_sprite",text="Reimport Sprite",icon="FILE_REFRESH")
                        
                    if get_addon_prefs(context).json_export:
                        row = layout.row()
                        row.operator("object.export_to_json",text="Export Json",icon="EXPORT",emboss=True)
                    
                    row = layout.row()
                    row.operator("coa_tools.create_slot_object",text="Merge to Slot Object",icon="IMASEL",emboss=True)  
                    
                    if get_addon_prefs(context).dragon_bones_export:
                        row = layout.row()
                        row.operator("coa_tools.export_dragon_bones",text="Export Dragonbones",icon_value=db_icon.icon_id,emboss=True)
                    
                row = layout.row(align=True)
                row.label(text="Edit Operator:")
                
                if context.active_object.type == "ARMATURE" and context.active_object.mode == "POSE":
                    row = layout.row(align=True)
                    row.operator("bone.coa_draw_bone_shape",text="Draw Bone Shape",icon="BONE_DATA")
                row = layout.row(align=True)
                if sprite_object.coa_edit_mesh == False and sprite_object.coa_edit_armature == False and sprite_object.coa_edit_weights == False and not(obj.type == "MESH" and obj.mode=="EDIT"):  
                    row.operator("scene.coa_quick_armature",text="Edit Armature",icon="ARMATURE_DATA")
                elif sprite_object.coa_edit_armature:
                    row.prop(sprite_object,"coa_edit_armature", text="Finish Edit Armature",icon="ARMATURE_DATA")
                if context.active_object != None and context.active_object.mode == "POSE":
                    row = layout.row(align=True)
                    row.label(text="Bone Constraint Operator:")
                    row = layout.row(align=True)
                    row.operator("object.coa_set_ik",text="Create IK Bone",icon="CONSTRAINT_BONE")
                    row = layout.row(align=True)
                    row.operator("bone.coa_set_stretch_bone",text="Create Stretch Bone",icon="CONSTRAINT_BONE")

            if context.active_object.type == "MESH":
                if sprite_object.coa_edit_mesh == False and sprite_object.coa_edit_armature == False and sprite_object.coa_edit_weights == False:
                    row = layout.row(align=True)
                    row.operator("object.coa_edit_mesh",text="Edit Mesh",icon="GREASEPENCIL")
                elif sprite_object.coa_edit_mesh:
                    row = layout.row(align=True)
                    row.prop(sprite_object,"coa_edit_mesh", text="Finish Edit Mesh", toggle=True, icon="GREASEPENCIL")
            
                if sprite_object.coa_edit_mesh == False and sprite_object.coa_edit_armature == False and sprite_object.coa_edit_weights == False and not(obj.type == "MESH" and obj.mode=="EDIT") and (sprite_object) != None:
                    row = layout.row(align=True)
                    row.operator("object.coa_edit_weights",text="Edit Weights",icon="MOD_VERTEX_WEIGHT")
                    row = layout.row(align=True)
                    row.operator("action.rhubarb_lipsync", text="Lipsync", icon="CLIP")
                elif sprite_object.coa_edit_weights:
                    row = layout.row(align=True)
                    row.prop(sprite_object,"coa_edit_weights", text="Finish Edit Weights", toggle=True, icon="MOD_VERTEX_WEIGHT")
                    
                    col = layout.split().column()
                    tool_settings = scene.tool_settings
                    brush_data = tool_settings.weight_paint
                    
                    col.template_ID_preview(brush_data, "brush", new="brush.add", rows=3, cols=8)
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings,"weight")
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings,"size")
                    row.prop(tool_settings.unified_paint_settings,"use_pressure_size",text="")
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings,"strength")
                    row.prop(tool_settings.unified_paint_settings,"use_pressure_strength",text="")
                    row = col.row(align=True)
                    row.prop(tool_settings,"use_auto_normalize",text="Auto Normalize")

        if context.active_object != None and "coa_sprite" in obj and context.active_object.mode == "EDIT" and context.active_object.type == "MESH" and sprite_object.coa_edit_mesh:
            row = layout.row(align=True)
            row.label(text="Mesh Tools:")
            
            row = layout.row(align=True)
            operator = row.operator("object.coa_fill",text="Normal Fill",icon="OUTLINER_OB_SURFACE")
            operator.triangulate = False
            
            row = layout.row(align=True)
            operator = row.operator("object.coa_fill",text="Triangle Fill",icon="OUTLINER_OB_SURFACE")
            operator.triangulate = True
            
            col = layout.column(align=True)
            row2 = col.row(align=True)
            row2.prop(scene,'coa_snap_distance',text="Merge Distance")
            
            row2 = col.row(align=True)
            row2.prop(scene,'coa_distance',text="Stroke Distance")
            row2.operator("coa_tools.pick_edge_length",text="",icon="EYEDROPPER")
            row2.row(align=True).prop(scene,'coa_distance_constraint',text="",icon="CONSTRAINT")
            
            row2 = col.row(align=True)
            row2.prop(scene,'coa_surface_snap',text="Snap Vertices",icon="SNAP_SURFACE")
            
            row2 = col.row(align=True)
            row2.prop(scene,'coa_automerge',text="Merge Vertices",toggle=True,icon="AUTOMERGE_ON")
            
            row2 = col.row(align=True)
            if scene.coa_lock_to_bounds:
                row2.prop(scene,"coa_lock_to_bounds",text="Draw only within Bounds",icon="LOCKVIEW_ON")
            else:
                row2.prop(scene,"coa_lock_to_bounds",text="Draw everywhere",icon="LOCKVIEW_OFF")
            
            col = layout.column(align=True)
            operator = col.operator("mesh.knife_tool", text="Knife")
            operator = col.operator("coa_tools.reproject_sprite_texture", text="Reproject Sprite")

### Custom template_list look
class UIListAnimationCollections(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        ob = data
        slot = item
        col = layout.row(align=True)
        if item.name not in ["NO ACTION","Restpose"]:
            col.label(icon="ACTION")
            col.prop(item,"name",emboss=False,text="")
        elif item.name == "NO ACTION":
            col.label(icon="RESTRICT_SELECT_ON")    
            col.label(text=item.name)
        elif item.name == "Restpose":
            col.label(icon="ARMATURE_DATA")    
            col.label(text=item.name)
        
        if context.scene.coa_nla_mode == "NLA" and item.name not in ["NO ACTION","Restpose"]:    
            col = layout.row(align=False)
            op = col.operator("coa_operator.create_nla_track",icon="NLA",text="")
            op.anim_collection_name = item.name

### Custom template_list look for event lists            
class UIListEventCollection(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        ob = data
        slot = item
        col = layout.column(align=False)
        
        row = col.row(align=True)
        row.label(text="",icon="TIME")
        row.prop(item,"frame",emboss=False,text="Frame")
        op = row.operator("coa_tools.remove_timeline_event",text="",icon="PANEL_CLOSE",emboss=False)
        op.index = index
        
        row = col.row(align=True)
        row.prop(item,"event",emboss=True,text="Event")
        row.prop(item,"action",emboss=True,text="Action")
        row.prop(item,"sound",emboss=True,text="Sound")
        
        


######################################################################################################################################### Select Child Operator
class SelectChild(bpy.types.Operator):
    bl_idname = "object.coa_select_child"
    bl_label = "select_child"
    
    ob_name = StringProperty()
    bone_name = StringProperty()
    
    def __init__(self):
        self.sprite_object = None
    
    mode = EnumProperty(items=(("object","object","object"),("bone","bone","bone")))
    def select_child(self,context):
        if self.mode == "object":
            ob = bpy.data.objects[self.ob_name]
            ob.coa_hide_select = False
            ob.coa_hide = False
            ob.select = not(ob.select)
            context.scene.objects.active = ob
                
        elif self.mode == "bone":
            armature_ob = bpy.data.objects[self.ob_name]
            armature = bpy.data.armatures[armature_ob.data.name]
            bone = armature.bones[self.bone_name]
            bone.select = not bone.select
            bone.select_tail = not bone.select_tail
            bone.select_head = not bone.select_head
            if bone.select == True:
                armature.bones.active = bone
            else:
                armature.bones.active = None
        
    def shift_select_child(self,context):
        sprite_object = get_sprite_object(context.active_object)
        children = []
        armature = None
        if self.mode == "object":
            children = get_children(context,sprite_object,ob_list=[])
        else:
            armature = bpy.data.armatures[self.ob_name]
            for bone in  armature.bones:
                children.append(bone)
        from_index = 0
        to_index = 0
        for i,child in enumerate(children):
            if self.mode == "object":
                if child.name == self.ob_name:
                    to_index = i
            elif self.mode == "bone":
                if child.name == self.bone_name:
                    to_index = i
            if child.select == True:
                from_index = i

        select_range = []
        if from_index < to_index:
            for i in range(from_index,to_index+1):
                select_range.append(i)
        else:
            for i in range(to_index,from_index):
                select_range.append(i)  
        for i,child in enumerate(children):
            if i in select_range:
                child.coa_hide_select = False
                child.coa_hide = False
                child.select = True
                
        if self.mode == "object":
            context.scene.objects.active = bpy.data.objects[self.ob_name]
        elif self.mode == "bone":
            context.scene.objects.active = bpy.data.objects[self.ob_name]
            armature.bones.active  = armature.bones[self.bone_name]
        
    def change_weight_mode(self,context,mode):
        if self.sprite_object.coa_edit_weights:
            armature = get_armature(self.sprite_object)
            armature.select = True
            bpy.ops.object.mode_set(mode=mode)
            bpy.ops.view3d.localview()
            global tmp_active_object
            tmp_active_object = context.active_object
            
    def invoke(self,context,event):
        self.sprite_object = get_sprite_object(context.active_object)
        if self.sprite_object != None:
            self.change_weight_mode(context,"OBJECT")
        
        if self.sprite_object != None:    
            if event.shift and not self.sprite_object.coa_edit_weights:
                self.shift_select_child(context)
            if not self.sprite_object.coa_edit_weights or ( self.sprite_object.coa_edit_weights and bpy.data.objects[self.ob_name].type == "MESH"):
                if not event.ctrl and not event.shift:
                    for child in context.selected_objects:
                        child.select = False
                    if self.mode == "bone":
                        for bone in bpy.data.objects[self.ob_name].data.bones:
                            bone.select = False
                            bone.select_head = False
                            bone.select_tail = False
                if not event.shift:
                    self.select_child(context)
            if self.sprite_object.coa_edit_weights:     
                create_armature_parent(context)
            self.change_weight_mode(context,"WEIGHT_PAINT")    
        else:
            self.shift_select_child(context)
                        
        return{'FINISHED'}
    
class CutoutAnimationCollections(bpy.types.Panel):
    bl_idname = "cutout_animation_collections"
    bl_label = "Cutout Animations"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Cutout Animation"
    
    
    def set_actions(self,context):
        scene = context.scene
        sprite_object = get_sprite_object(context.active_object)
        
        if context.scene.coa_nla_mode == "ACTION":
            scene.frame_start = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].frame_start
            scene.frame_end = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].frame_end
            set_action(context)
        for obj in context.visible_objects:
            if obj.type == "MESH" and "coa_sprite" in obj:
                update_uv(context,obj)
                set_alpha(obj,bpy.context,obj.coa_alpha)
                set_z_value(context,obj,obj.coa_z_value)
                set_modulate_color(obj,context,obj.coa_modulate_color)
        
        ### set export name
        if scene.coa_nla_mode == "ACTION":
            action_name = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].name    
            if action_name in ["Restpose","NO ACTION"]:
                action_name = ""
            else:
                action_name += "_"
            path = context.scene.render.filepath.replace("\\","/")
            dirpath = path[:path.rfind("/")]
            final_path = dirpath + "/" + action_name
            context.scene.render.filepath = final_path

    
    def set_nla_mode(self,context):
        sprite_object = get_sprite_object(context.active_object)
        children = get_children(context,sprite_object,ob_list=[])
        if self.coa_nla_mode == "NLA":
            for child in children:
                if child.animation_data != None:
                    child.animation_data.action = None
            context.scene.frame_start = context.scene.coa_frame_start
            context.scene.frame_end = context.scene.coa_frame_end        
            
            for child in children:
                if child.animation_data != None:
                    for track in child.animation_data.nla_tracks:
                        track.mute = False
        else:
            anim_collection = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index]
            context.scene.frame_start = anim_collection.frame_start
            context.scene.frame_end = anim_collection.frame_end
            set_action(context)            
            for obj in context.visible_objects:
                if obj.type == "MESH" and "coa_sprite" in obj:
                    update_uv(context,obj)
                    set_alpha(obj,bpy.context,obj.coa_alpha)
                    set_z_value(context,obj,obj.coa_z_value)
                    set_modulate_color(obj,context,obj.coa_modulate_color)
            for child in children:
                if child.animation_data != None:
                    for track in child.animation_data.nla_tracks:
                        track.mute = True
                
    
    
    
    def update_frame_range(self,context):
        sprite_object = get_sprite_object(context.active_object)
        if len(sprite_object.coa_anim_collections) > 0:
            anim_collection = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index]
        
        if context.scene.coa_nla_mode == "NLA" or len(sprite_object.coa_anim_collections) == 0:
            context.scene.frame_start = self.coa_frame_start
            context.scene.frame_end = self.coa_frame_end
    
    bpy.types.Object.coa_anim_collections_index = IntProperty(update=set_actions)
    bpy.types.Scene.coa_nla_mode = EnumProperty(description="Animation Mode. Can be set to NLA or Action to playback all NLA Strips or only Single Actions",items=(("ACTION","ACTION","ACTION","ACTION",0),("NLA","NLA","NLA","NLA",1)),update=set_nla_mode)
    bpy.types.Scene.coa_frame_start = IntProperty(name="Frame Start",default=0,min=0,update=update_frame_range)
    bpy.types.Scene.coa_frame_end = IntProperty(name="Frame End",default=250,min=1,update=update_frame_range)
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        scene = context.scene
        sprite_object = get_sprite_object(obj)
        if obj != None and sprite_object != None:
            
            row = layout.row()
            row.prop(sprite_object,"coa_animation_loop",text="Wrap Animation Playback")
            
            row = layout.row()
            row.prop(scene,"coa_nla_mode",expand=True)
            
            if scene.coa_nla_mode == "NLA":
                row = layout.row(align=True)
                row.prop(scene,"coa_frame_start")
                row.prop(scene,"coa_frame_end")
            
            row = layout.row()
            row.template_list("UIListAnimationCollections","dummy",sprite_object, "coa_anim_collections", sprite_object, "coa_anim_collections_index",rows=1,maxrows=10,type='DEFAULT')
            col = row.column(align=True)
            col.operator("my_operator.add_animation_collection",text="",icon="ZOOMIN")
            col.operator("my_operator.remove_animation_collection",text="",icon="ZOOMOUT")
            
            
            if  len(sprite_object.coa_anim_collections) > 0 and sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].action_collection:
                row = layout.row(align=True)
                item = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index]
                row.prop(item,"frame_end",text="Animation Length")
                
                
                if get_addon_prefs(context).dragon_bones_export:
                    row = layout.row(align=True)
                    row.label(text="Timeline Events",icon="TIME")
                    row = layout.row(align=False)
                    row.template_list("UIListEventCollection","dummy",item, "event", item, "event_index",rows=1,maxrows=10,type='DEFAULT')
                    col = row.column(align=True)
                    col.operator("coa_tools.add_timeline_event",text="",icon="ZOOMIN")
                    #row.prop(sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index],"frame_end",text="End")    
            
            row = layout.row(align=True)
            operator = row.operator("coa_tools.batch_render",text="Batch Render Animations",icon="RENDER_ANIMATION")                  

preview_collections = {}
