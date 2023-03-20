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
from .. ui import preview_collections
import bpy.utils.previews

    
class COATOOLS_OT_SelectFrameThumb(bpy.types.Operator):
    bl_idname = "coa_tools.select_frame_thumb"
    bl_label = "Select Frame Thumb"
    bl_description = "Loads all Spritesheet frames and generates a thumbnail preview. Can take a while when loading the first time."
    bl_options = {"REGISTER"}
    

    @classmethod
    def poll(cls, context):
        return True
    
    
    def draw(self, context):
        obj = context.active_object
        layout = self.layout

        row = layout.row()
        row.scale_y = .8
        row.template_icon_view(obj.coa_tools, "sprite_frame_previews",scale=5)
    
    def invoke(self, context, event):
        obj = context.active_object

        if obj.coa_tools.type == "SLOT" and len(obj.coa_tools.slot) > 0:
            wm = context.window_manager
            try:
                obj.coa_sprite_frame_previews = str(obj.coa_tools.slot_index)
            except:
                pass    
            return wm.invoke_popup(self, width=100)
        else:
            self.report({'INFO'},"Object has no Sprites.")
            return {"FINISHED"}
    
    def execute(self, context):
        return {"FINISHED"}
        
class COATOOLS_OT_CreateSpritesheetPreview(bpy.types.Operator):
    bl_idname = "coa_tools.create_spritesheet_preview"
    bl_label = "Create Spritesheet Preview"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True
    
    
    def execute(self, context):
        
        
        thumb_size = get_addon_prefs(context).sprite_thumb_size
        
        obj = context.active_object
        thumb_dir_path = os.path.join(context.preferences.filepaths.temporary_directory,"coa_thumbs")
        if obj.coa_tiles_changed or not os.path.exists(thumb_dir_path):
            spritesheet = obj.material_slots[0].material.texture_slots[0].texture.image
            assign_tex_to_uv(spritesheet,obj.data.uv_textures[0])
            
            obj.coa_tiles_changed = False
            if "coa_sprite" in obj:
                if not os.path.exists(thumb_dir_path):
                    os.makedirs(thumb_dir_path)
                
                material_slot = None                        
                img = None
                tex_slot = None
                for slot in obj.material_slots:
                    if slot != None:
                        if slot.material != None:
                            material_slot = slot
                            break
                if material_slot == None:
                    return{'FINISHED'}        
                for slot in material_slot.material.texture_slots:
                    if slot != None:
                        tex_slot = slot
                        img = slot.texture.image
                        break
                #img = obj.material_slots[0].material.texture_slots[0].texture.image
                sprite_dimension = [img.size[0]/obj.coa_tiles_x,img.size[1]/obj.coa_tiles_y]
                uv_layer = tex_slot.uv_layer
                uv_textures = obj.data.uv_textures
                if uv_layer == "":
                    tex_slot.uv_layer = obj.data.uv_textures[0].name
                
                uv_texture = None
                if "preview_render_uv" not in uv_textures:
                    uv_texture = uv_textures.new(name="preview_render_uv")
                else:
                    uv_texture = uv_textures["preview_render_uv"]    
                uv_layer = obj.data.uv_layers[uv_texture.name]
                unwrap_with_bounds(obj,1)
                
                if sprite_dimension[0] > sprite_dimension[1]:
                    preview_dimension = [thumb_size,int(sprite_dimension[1]*(thumb_size/sprite_dimension[0]))]
                else:
                    preview_dimension = [int(sprite_dimension[0]*(thumb_size/sprite_dimension[1])),thumb_size]
                obj.data.uv_textures.active = obj.data.uv_textures[0]
                
                ### itereate over all frames of a spritesheet and generate thumbnail icons
                bake_type = bpy.context.scene.render.bake_type
                render_margin = bpy.context.scene.render.bake_margin
                bpy.context.scene.render.bake_margin = 0
                init_sprite_frame = obj.coa_sprite_frame
                for i in range(obj.coa_tiles_x * obj.coa_tiles_y):
                    obj.coa_sprite_frame = i
                    obj.data.uv_textures.active = obj.data.uv_textures[1]
                    
                    img_name = "thumb_"+obj.name+"_"+str(i).zfill(3)
                    
                    if img_name not in bpy.data.images:
                        img = bpy.data.images.new(img_name,preview_dimension[0],preview_dimension[1],True)
                    else:
                        img = bpy.data.images[img_name]
                    assign_tex_to_uv(img,obj.data.uv_textures[1])
                    
                    bpy.context.scene.render.bake_type = "TEXTURE"
                    bpy.ops.object.bake_image()
                    obj.data.uv_textures.active = obj.data.uv_textures[0]

                    img.save_render(os.path.join(thumb_dir_path, img.name+".png"))
                    img.user_clear()
                    bpy.data.images.remove(img)
                    
                    
                
                ### set back everything
                bpy.context.scene.render.bake_margin = render_margin
                bpy.context.scene.render.bake_type = bake_type    
                obj.coa_sprite_frame = init_sprite_frame
                if uv_texture.name in obj.data.uv_textures:
                    obj.data.uv_textures.remove(uv_texture)        
                
        return {"FINISHED"}
    
            