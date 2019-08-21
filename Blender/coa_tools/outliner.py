import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, FloatProperty, StringProperty, EnumProperty, PointerProperty, CollectionProperty
# from . functions import *
from . import functions
from bpy.app.handlers import persistent

def select_outliner_object(self, context):
    selected_item = self.outliner[self.outliner_index]
    sprite_object = bpy.data.objects[selected_item.sprite_object_name]
    edit_mode_active = sprite_object != None and (sprite_object.coa_tools.edit_mesh or sprite_object.coa_tools.edit_armature or sprite_object.coa_tools.edit_weights or sprite_object.coa_tools.edit_shapekey)
    if selected_item.entry_type in ["SPRITE", "OBJECT"] and not edit_mode_active:
        selected_object = context.view_layer.objects[selected_item.name]
        for obj in context.view_layer.objects:
            obj.select_set(False)
        for item in self.outliner:
            if item.selected:
                bpy.data.objects[item.name].select_set(True)
        context.view_layer.objects.active = selected_object

def set_hide(self, value):
    if self.entry_type in ["OBJECT", "SPRITE", "BONE_PARENT"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        selected_object.hide_set(value)
        self["hide"] = value
    elif self.entry_type in ["BONE"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        bone = selected_object.data.bones[self.display_name]
        self["hide"] = value
        bone.hide = value

def get_hide(self):
    if self.entry_type in ["OBJECT", "SPRITE", "BONE_PARENT"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        return selected_object.hide_get()
    elif self.entry_type in ["BONE"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        bone = selected_object.data.bones[self.display_name]
        return bone.hide
    else:
        return False

def set_hide_select(self, value):
    if self.entry_type in ["OBJECT", "SPRITE", "BONE_PARENT"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        selected_object.hide_select = value
        self["hide_select"] = value
    elif self.entry_type in ["BONE"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        bone = selected_object.data.bones[self.display_name]
        self["hide_select"] = value
        bone.hide_select = value

def get_hide_select(self):
    if self.entry_type in ["OBJECT", "SPRITE", "BONE_PARENT"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        return selected_object.hide_select
    elif self.entry_type in ["BONE"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        bone = selected_object.data.bones[self.display_name]
        return bone.hide_select
    else:
        return False

def set_favorite(self, value):
    if self.entry_type in ["OBJECT", "SPRITE", "BONE_PARENT"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        selected_object.coa_tools.favorite = value
        self["favorite"] = value
    elif self.entry_type in ["BONE"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        bone = selected_object.data.bones[self.display_name]
        self["favorite"] = value
        bone.coa_tools.favorite = value

def get_favorite(self):
    if self.entry_type in ["OBJECT", "SPRITE", "BONE_PARENT"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        return selected_object.coa_tools.favorite
    elif self.entry_type in ["BONE"]:
        selected_object = bpy.context.view_layer.objects[self.name]
        bone = selected_object.data.bones[self.display_name]
        return bone.coa_tools.favorite
    else:
        return False

class COAOutliner(bpy.types.PropertyGroup):
    name: StringProperty(name="Sprite Name")
    display_name: StringProperty(name="Name")
    index: IntProperty()
    object_type: StringProperty()
    entry_type: StringProperty(default="SPRITE") # ["SPRITE", "OBJECT","SLOT", "BONE", "BONE_PARENT"]
    hierarchy_level: IntProperty()
    slot_type: StringProperty()
    selected: BoolProperty(default=False)
    active: BoolProperty(default=False)
    hide: BoolProperty(default=False, set=set_hide, get=get_hide)
    hide_select: BoolProperty(default=False, set=set_hide_select, get=get_hide_select)
    favorite: BoolProperty(default=False, set=set_favorite, get=get_favorite)
    sprite_object_name: StringProperty()
    slot_index: IntProperty()

class COATOOLS_UL_Outliner(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        active_object = context.active_object
        obj = bpy.data.objects[item.name] if item.entry_type in ["SPRITE","OBJECT"] else None
        col = layout.grid_flow(row_major=True, columns=2)
        # master_row = col.row(align=True)
        row_left = col.row(align=False)
        row_left.alignment = "LEFT"
        row_right = col.row(align=True)
        row_right.alignment = "RIGHT"
        row_active = layout.row(align=True)
        sprite_object = bpy.data.objects[item.sprite_object_name] if item.sprite_object_name in bpy.data.objects else None

        edit_mode_active = sprite_object != None and (sprite_object.coa_tools.edit_mesh or sprite_object.coa_tools.edit_armature or sprite_object.coa_tools.edit_weights or sprite_object.coa_tools.edit_shapekey)
        if edit_mode_active:
            row_left.active = False
            row_right.active = False
            row_left.enabled = False
            row_right.enabled = False

        selected_icon = "LAYER_ACTIVE" if item.selected else "LAYER_USED"
        hide_icon = "HIDE_ON" if item.hide else "HIDE_OFF"
        hide_select_icon = "RESTRICT_SELECT_ON" if item.hide_select else "RESTRICT_SELECT_OFF"
        favorite_icon = "SOLO_ON" if item.favorite else "SOLO_OFF"
        show_children_icon = "DISCLOSURE_TRI_RIGHT" if obj != None and not obj.coa_tools.show_children else "DISCLOSURE_TRI_DOWN"

        icon = "NONE"
        if item.object_type == "ARMATURE":
            icon = "ARMATURE_DATA"
        elif item.object_type == "MESH":
            icon = "TEXTURE"
        elif item.object_type == "CAMERA":
            icon = "VIEW_CAMERA"
        elif item.object_type == "LIGHT":
            icon = "LIGHT"

        for i in range(item.hierarchy_level):
            row_left.separator()

        if item.entry_type in ["SPRITE","OBJECT"]:
            row_left.label(text="", icon=selected_icon)
            row_left.label(text="", icon=icon)
            if item.object_type == "ARMATURE":
                row_left.prop(obj.coa_tools, "show_children", text="", emboss=False, icon=show_children_icon)

            op = row_left.operator("coa_tools.select_child", text=item.name, emboss=False)
            op.mode = "object"
            op.outliner_index = item.index
            op.ob_name = item.name

            if len(obj.coa_tools.slot) > 0:
                if obj.coa_tools.slot_show:
                    row_right.prop(obj.coa_tools, "slot_show", text="", icon="TRIA_DOWN", emboss=False)
                else:
                    row_right.prop(obj.coa_tools, "slot_show", text="", icon="TRIA_LEFT", emboss=False)

            if obj != sprite_object:
                if not sprite_object.coa_tools.change_z_ordering:
                    row_right.prop(item, "favorite", text="", icon=favorite_icon, emboss=False)
                    row_right.prop(item, "hide", text="", icon=hide_icon, emboss=False)
                    row_right.prop(item, "hide_select", text="", icon=hide_select_icon, emboss=False)
                else:
                    if obj.type == "MESH":
                        children_names = []
                        for child in sprite_object.children:
                            if child.type == "MESH":
                                children_names.append(child.name)

                        op = row_right.operator("coa_tools.change_z_ordering", text="", icon="TRIA_DOWN")
                        op.index = i
                        op.direction = "DOWN"
                        op.active_sprite = item.name
                        op.all_sprites = str(children_names)
                        op = row_right.operator("coa_tools.change_z_ordering", text="", icon="TRIA_UP")
                        op.index = i
                        op.direction = "UP"
                        op.active_sprite = item.name
                        op.all_sprites = str(children_names)
            if obj.type == "ARMATURE":
                pose_icon = "POSE_HLT"
                if obj.mode == "OBJECT":
                    pose_icon = "OBJECT_DATAMODE"
                elif obj.mode == "EDIT":
                    pose_icon = "EDITMODE_HLT"
                op = row_right.operator("coa_tools.toggle_pose_mode", icon=pose_icon, text="", emboss=False)
                op.ob_name = obj.name
            if obj == sprite_object:
                op = row_right.operator("coa_tools.view_sprite", icon="ZOOM_SELECTED", text="", emboss=False)
                op.type = "VIEW_ALL"
                op.name = obj.name
                row_right.prop(obj.coa_tools, "change_z_ordering", text="", icon="SORTALPHA", emboss=False)

            if sprite_object != None and obj.type == "MESH" and sprite_object.coa_tools.edit_armature:
                op = row_active.operator("coa_tools.bind_mesh_to_bones", text="", icon="BONE_DATA", emboss=False)
                op.ob_name = item.name
        elif item.entry_type == "SLOT":
            obj = bpy.data.objects[item.name]
            slot = obj.coa_tools.slot[item.slot_index]
            if slot.active:
                row_left.prop(slot, "active", text=slot.mesh.name, icon="CHECKBOX_HLT", emboss=False)
            else:
                row_left.prop(slot, "active", text=slot.mesh.name, icon="CHECKBOX_DEHLT", emboss=False)

            op = row_right.operator("coa_tools.move_slot_item", icon="TRIA_DOWN", emboss=False, text="")
            op.idx = item.slot_index
            op.ob_name = item.name
            op.mode = "DOWN"
            op = row_right.operator("coa_tools.move_slot_item", icon="TRIA_UP", emboss=False, text="")
            op.idx = item.slot_index
            op.ob_name = item.name
            op.mode = "UP"

            op = row_right.operator("coa_tools.remove_from_slot", icon="PANEL_CLOSE", emboss=False, text="")
            op.idx = item.slot_index
            op.ob_name = item.name
        elif item.entry_type == "BONE_PARENT":
            obj = bpy.data.objects[item.name]
            row_left.label(text="", icon="BONE_DATA")
            if obj.coa_tools.show_bones:
                row_right.prop(obj.coa_tools, "show_bones", text="", icon="TRIA_DOWN", emboss=False)
            else:
                row_right.prop(obj.coa_tools, "show_bones", text="", icon="TRIA_LEFT", emboss=False)

            row_left.label(text=item.display_name)
            row_right.prop(item, "favorite", text="", icon=favorite_icon, emboss=False)
            row_right.prop(item, "hide", text="", icon=hide_icon, emboss=False)
            row_right.prop(item, "hide_select", text="", icon=hide_select_icon, emboss=False)
        elif item.entry_type == "BONE":
            obj = bpy.data.objects[item.name]
            if obj.type == "ARMATURE":
                row_left.label(text="", icon=selected_icon)
                bone = obj.data.bones[item.display_name]
                row_left.label(text="", icon="BONE_DATA")

                # row_left.label(text=item.display_name)
                op = row_left.operator("coa_tools.select_child", text=item.display_name, emboss=False)
                op.mode = "bone"
                op.outliner_index = item.index
                op.ob_name = item.name
                op.bone_name = item.display_name

                if len(bone.children) > 0:
                    if bone.coa_tools.show_children:
                        row_right.prop(bone.coa_tools, "show_children", text="", icon="TRIA_DOWN", emboss=False)
                    else:
                        row_right.prop(bone.coa_tools, "show_children", text="", icon="TRIA_LEFT", emboss=False)

                row_right.prop(item, "favorite", text="", icon=favorite_icon, emboss=False)
                row_right.prop(item, "hide", text="", icon=hide_icon, emboss=False)
                row_right.prop(item, "hide_select", text="", icon=hide_select_icon, emboss=False)

i = -1
@persistent
def create_outliner_items(dummy):
    context = bpy.context
    scene = context.scene
    active_object = context.active_object
    outliner = context.scene.coa_tools.outliner
    outliner_index = context.scene.coa_tools.outliner_index
    for item in outliner:
        outliner.remove(0)

    items = []
    for sprite_object in scene.objects:
        if "sprite_object" in sprite_object.coa_tools:
            items.append(sprite_object)
            sorted_children = []
            for obj in sprite_object.children:
                sorted_children.append(obj)
            sorted_children.sort(key=lambda x: x.location.y, reverse=False)
    items += sorted_children

    sprite_object = None
    global i
    i = -1
    for obj in items:
        if "sprite_object" in obj.coa_tools:
            sprite_object = obj
        if (scene.coa_tools.outliner_filter_names in obj.name or sprite_object == obj) and (not scene.coa_tools.outliner_favorites or (scene.coa_tools.outliner_favorites and obj.coa_tools.favorite) or sprite_object == obj):
            if sprite_object == obj or ("sprite_object" not in obj.coa_tools and sprite_object.coa_tools.show_children):
                i += 1
                item = outliner.add()
                item["name"] = obj.name
                item["display_name"] = obj.name
                item["index"] = i
                item["entry_type"] = "SPRITE" if obj.type == "MESH" and "sprite" in obj.coa_tools else "OBJECT"
                item["object_type"] = obj.type
                item["hierarchy_level"] = 0 if obj == sprite_object else 1
                item["slot_type"] = obj.coa_tools.type
                item["selected"] = obj.select_get()
                item["active"] = (obj == active_object)
                item["hide"] = obj.hide_get()
                item["hide_select"] = obj.hide_select
                item["favorite"] = obj.coa_tools.favorite
                item["sprite_object_name"] = sprite_object.name


                # retrieve bones
                if obj.type == "ARMATURE" and sprite_object.coa_tools.show_children and ((scene.coa_tools.outliner_favorites and obj.coa_tools.favorite) or not scene.coa_tools.outliner_favorites):
                    i += 1
                    bone_item = outliner.add()
                    bone_item["name"] = obj.name
                    bone_item["index"] = i
                    bone_item["entry_type"] = "BONE_PARENT"
                    bone_item["display_name"] = "Bones"
                    bone_item["sprite_object_name"] = sprite_object.name
                    bone_item["hide"] = obj.hide_get()
                    bone_item["hide_select"] = obj.hide_select
                    bone_item["hierarchy_level"] = item["hierarchy_level"] + 3

                    if sprite_object.coa_tools.show_bones:
                        for bone in obj.data.bones:
                            if bone.parent == None:
                                hierarchy_level = bone_item["hierarchy_level"]
                                recursive_bone_iteration(scene, outliner, sprite_object, obj, item, bone, hierarchy_level)

                # retrieve slots
                if obj.coa_tools.type == "SLOT" and obj.coa_tools.slot_show and not sprite_object.coa_tools.change_z_ordering:
                    for slot in obj.coa_tools.slot:
                        i += 1
                        slot_item = outliner.add()
                        slot_item["name"] = obj.name
                        slot_item["display_name"] = slot.mesh.name
                        slot_item["index"] = i
                        slot_item["entry_type"] = "SLOT"
                        slot_item["hierarchy_level"] = item["hierarchy_level"] + 3
                        slot_item["slot_index"] = slot.index
                        slot_item["sprite_object_name"] = sprite_object.name

    if active_object != None and active_object.name in outliner:
        item = outliner[active_object.name]
        context.scene.coa_tools.outliner_index = item.index
        if active_object.type == "ARMATURE" and active_object.mode == "POSE":
            for i, item in enumerate(outliner):
                if context.active_pose_bone != None and item.display_name == context.active_pose_bone.name:
                    context.scene.coa_tools.outliner_index = item.index
                    break


def recursive_bone_iteration(scene, outliner, sprite_object, obj, parent_item, bone, hierarchy_level):
    global i

    if (scene.coa_tools.outliner_favorites and bone.coa_tools.favorite) or not scene.coa_tools.outliner_favorites:
        i += 1
        bone_item = outliner.add()
        bone_item["name"] = obj.name
        bone_item["display_name"] = bone.name
        bone_item["entry_type"] = "BONE"
        bone_item["index"] = i
        bone_item["sprite_object_name"] = sprite_object.name
        bone_item["hide"] = bone.hide
        bone_item["hide_select"] = bone.hide_select
        bone_item["selected"] = bone.select
        bone_item["hierarchy_level"] = parent_item["hierarchy_level"] + 1 + hierarchy_level
        for child in bone.children:
            if bone.coa_tools.show_children:
                recursive_bone_iteration(scene, outliner, sprite_object, obj, parent_item, child, hierarchy_level + 1)
