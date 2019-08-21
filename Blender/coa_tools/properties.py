import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, FloatProperty, StringProperty, EnumProperty, PointerProperty, CollectionProperty
# from . functions import *
from . import functions
from . import outliner

def hide_bone(self, context):
    self.hide = self.hide


def hide_select_bone(self, context):
    self.iddata.hide_select = self.hide_select


def hide(self, context):
    if self.id_data.hide_viewport != self.hide:
        self.id_data.hide_viewport = self.hide


def hide_select(self, context):
    if self.hide_select:
        self.id_data.select_set(False)
        if context.scene.view_layers[0].objects.active == self:
            context.scene.view_layers[0].objects.active = self.parent
    self.id_data.hide_select = self.hide_select


def set_z_value(self, context):
    if context.scene.view_layers[0].objects.active == self.id_data:
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                if obj != self.id_data:
                    obj.coa_tools.z_value = self.z_value
                functions.set_z_value(context, obj, self.z_value)


def set_alpha(self, context):
    if context.scene.view_layers[0].objects.active == self.id_data:
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                if obj != self.id_data:
                    obj.coa_tools.alpha = self.alpha
                functions.set_alpha(obj, context, self.alpha)


def set_modulate_color(self, context):
    if context.scene.view_layers[0].objects.active == self.id_data:
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                if obj != self.id_data:
                    obj.coa_tools.modulate_color = self.modulate_color
                functions.set_modulate_color(obj, context, self.modulate_color)


def set_sprite_frame(self, context):
    if self.type == "MESH":
        self.coa_sprite_frame_last = -1
        self.coa_sprite_frame = int(self.coa_sprite_frame_previews)
        if context.scene.tool_settings.use_keyframe_insert_auto:
            bpy.ops.coa_tools.add_keyframe(prop_name="coa_sprite_frame", interpolation="CONSTANT")
    elif self.type == "SLOT":
        self.slot_index = int(self.sprite_frame_previews)


def exit_edit_weights(self, context):
    if not self.edit_weights:
        obj = context.active_object
        if obj != None and obj.mode == "WEIGHT_PAINT":
            bpy.ops.object.mode_set(mode="OBJECT")
        sprite_object = functions.get_sprite_object(obj)
        armature = functions.get_armature(sprite_object)
        armature.data.pose_position = "POSE"


def exit_edit_shapekey(self, context):
    if not self.edit_weights:
        obj = context.active_object
        if obj != None and obj.mode == "SCULPT":
            bpy.ops.object.mode_set(mode="OBJECT")
            obj.show_wire = False
            obj.show_only_shape_key = False


def hide_base_sprite(self, context):
    # hide_base_sprite(self)
    functions.hide_base_sprite(context.active_object)


def change_slot_mesh(self, context):
    self.slot_index_last = -1
    self.slot_index_last = self.id_data.coa_tools.slot_index
    functions.change_slot_mesh_data(context, self.id_data)
    self.id_data.data.coa_tools.hide_base_sprite = self.id_data.data.coa_tools.hide_base_sprite


def change_edit_mode(self, context):
    if self.edit_mesh == False:
        bpy.ops.object.mode_set(mode="OBJECT")
        functions.set_local_view(False)


def update_filter(self, context):
    pass


def get_shapekeys(self, context):
    SHAPEKEYS = []
    obj = context.active_object
    if obj.data.shape_keys != None:
        for i, shape in enumerate(obj.data.shape_keys.key_blocks):
            SHAPEKEYS.append((str(i), shape.name, shape.name, "SHAPEKEY_DATA", i))
    return SHAPEKEYS


def select_shapekey(self, context):
    if self.id_data.data.shape_keys != None:
        self.id_data.active_shape_key_index = int(self.selected_shapekey)

def enum_sprite_previews(self, context):
    """EnumProperty callback"""
    enum_items = []
    if context is None:
        return enum_items

    if self.type == "SLOT":
        for i, slot in enumerate(self.slot):
            if slot.mesh != None:
                mat = slot.mesh.materials[0]
                for node in mat.node_tree.nodes:
                    if node.label == "COA Material":
                        tex_node = node.inputs["Texture Color"].links[0].from_node
                        if tex_node != None:
                            img = tex_node.image
                            icon = bpy.types.UILayout.icon(img)
                            enum_items.append((str(i), slot.mesh.name, "", icon, i))

    return enum_items

def snapping(self,context):
    if self.surface_snap:
        bpy.context.scene.tool_settings.use_snap = True
        bpy.context.scene.tool_settings.snap_elements = {'FACE'}
    else:
        bpy.context.scene.tool_settings.use_snap = False

def update_stroke_distance(self,context):
    mult = bpy.context.space_data.region_3d.view_distance*.05
    if self.distance_constraint:
        context.scene.coa_distance /= mult
    else:
        context.scene.coa_distance *= mult

def lock_view(self,context):
    scenes = []
    scenes.append(context.scene)

    for scene in bpy.data.scenes:
        if scene not in scenes:
            scenes.append(scene)

    for scene in scenes:
        if scene != self.id_data:
            scene.coa_tools["view"] = self["view"]
        if self.view == "3D":
            functions.set_view(scene, "3D")
        elif self.view == "2D":
            functions.set_view(scene, "2D")
    if self.view == "3D":
        functions.set_middle_mouse_move(False)
    elif self.view == "2D":
        functions.set_middle_mouse_move(True)


COLLECTIONS = []
def get_collection_recursive(collection):
    global COLLECTIONS
    if len(collection.children) > 0:
        for child in collection.children:
            COLLECTIONS.append(child)
            get_collection_recursive(child)


def get_available_collections(self, context):
    global COLLECTIONS
    COLLECTIONS = []
    get_collection_recursive(context.scene.collection)
    ITEMS = []
    for i, child_collection in enumerate(COLLECTIONS):
        ITEMS.append((child_collection.name,child_collection.name,"","GROUP",i))
    return ITEMS


def set_actions(self, context):
    scene = context.scene
    sprite_object = functions.get_sprite_object(context.active_object)

    index = min(len(sprite_object.coa_tools.anim_collections) - 1, sprite_object.coa_tools.anim_collections_index)
    if context.scene.coa_tools.nla_mode == "ACTION":
        scene.frame_start = sprite_object.coa_tools.anim_collections[index].frame_start
        scene.frame_end = sprite_object.coa_tools.anim_collections[index].frame_end
        functions.set_action(context)
    for obj in context.visible_objects:
        if obj.type == "MESH" and "coa_sprite" in obj:
            functions.set_alpha(obj, bpy.context, obj.coa_tools.alpha)
            functions.set_z_value(context, obj, obj.coa_tools.z_value)
            functions.set_modulate_color(obj, context, obj.coa_tools.modulate_color)

    ### set export name
    if scene.coa_tools.nla_mode == "ACTION":
        action_name = sprite_object.coa_tools.anim_collections[index].name
        if action_name in ["Restpose","NO ACTION"]:
            action_name = ""
        else:
            action_name += "_"
        path = context.scene.render.filepath.replace("\\","/")
        dirpath = path[:path.rfind("/")]
        final_path = dirpath + "/" + action_name
        context.scene.render.filepath = final_path


def set_nla_mode(self, context):
    sprite_object = functions.get_sprite_object(context.active_object)
    children = functions.get_children(context,sprite_object,ob_list=[])
    if self.nla_mode == "NLA":
        for child in children:
            if child.animation_data != None:
                child.animation_data.action = None
        context.scene.frame_start = context.scene.coa_tools.frame_start
        context.scene.frame_end = context.scene.coa_tools.frame_end

        for child in children:
            if child.animation_data != None:
                for track in child.animation_data.nla_tracks:
                    track.mute = False
    else:
        if len(sprite_object.coa_tools.anim_collections) > 0:
            anim_collection = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]
            context.scene.frame_start = anim_collection.frame_start
            context.scene.frame_end = anim_collection.frame_end
            functions.set_action(context)
            for obj in context.visible_objects:
                if obj.type == "MESH" and "coa_sprite" in obj:
                    functions.set_alpha(obj,bpy.context,obj.coa_tools.alpha)
                    functions.set_z_value(context,obj,obj.coa_tools.z_value)
                    functions.set_modulate_color(obj,context,obj.coa_tools.modulate_color)
            for child in children:
                if child.animation_data != None:
                    for track in child.animation_data.nla_tracks:
                        track.mute = True

    bpy.ops.coa_tools.toggle_animation_area(mode="UPDATE")


def update_frame_range(self,context):
    sprite_object = functions.get_sprite_object(context.active_object)
    if len(sprite_object.coa_tools.anim_collections) > 0:
        anim_collection = sprite_object.coa_tools.anim_collections[sprite_object.coa_tools.anim_collections_index]

    if context.scene.coa_tools.nla_mode == "NLA" or len(sprite_object.coa_tools.anim_collections) == 0:
        context.scene.frame_start = self.coa_tools.frame_start
        context.scene.frame_end = self.coa_tools.frame_end

def set_blend_mode(self, context):
    self.id_data.active_material.blend_method = self.blend_mode

class UVData(bpy.types.PropertyGroup):
    uv: FloatVectorProperty(default=(0,0),size=2)

class SlotData(bpy.types.PropertyGroup):
    def change_slot_mesh(self, context):
        context
        obj = self.id_data
        self["active"] = True
        if self.active:
            obj.coa_tools.slot_index = self.index
            functions.hide_base_sprite(obj)
            for slot in obj.coa_tools.slot:
                if slot != self:
                    slot["active"] = False

    mesh: bpy.props.PointerProperty(type=bpy.types.Mesh)
    offset: FloatVectorProperty()
    name: StringProperty()
    active: BoolProperty(update=change_slot_mesh)
    index: IntProperty()

class Event(bpy.types.PropertyGroup):
    name: StringProperty()
    type: EnumProperty(name="Object Type",default="SOUND",items=(("SOUND","Sound","Sound","SOUND",0),("EVENT","Event","Event","PHYSICS",1)))
    value: StringProperty(description="Define which sound or event key is triggered.")

class TimelineEvent(bpy.types.PropertyGroup):
    def change_event_order(self, context):
        timeline_events = self.id_data.coa_tools.anim_collections[self.id_data.coa_tools.anim_collections_index].timeline_events
        for i, event in enumerate(timeline_events):
            event_next = None
            if i < len(timeline_events)-1:
                event_next = timeline_events[i+1]
            if event_next != None and event_next.frame < event.frame:
                timeline_events.move(i+1, i)

    event: CollectionProperty(type=Event)
    frame: IntProperty(default=0, min=0, update=change_event_order)
    collapsed: BoolProperty(default=False)

class AnimationCollections(bpy.types.PropertyGroup):
    def set_frame_start(self,context):
        bpy.context.scene.frame_start = self.frame_start
    def set_frame_end(self,context):
        bpy.context.scene.frame_end = self.frame_end

    def check_name(self, context):
        sprite_object = functions.get_sprite_object(context.active_object)

        if self.name_old != "" and self.name_change_to != self.name:
            name_array = []
            for item in sprite_object.coa_tools.anim_collections:
                name_array.append(item.name_old)
            self.name_change_to = functions.check_name(name_array,self.name)
            self.name = self.name_change_to

        children = functions.get_children(context, sprite_object, ob_list=[])
        objs = []
        if sprite_object.type == "ARMATURE":
            objs.append(sprite_object)
        for child in children:
            objs.append(child)

        for child in objs:
            action_name = self.name_old + "_" + child.name
            action_name_new = self.name + "_" + child.name

            # if action_name_new in bpy.data.actions:
            #     bpy.data.actions.remove(bpy.data.actions[action_name])
            if action_name_new in bpy.data.actions:
                print(child.name,"",action_name_new , " -- ",action_name_new in bpy.data.actions)
            if action_name_new not in bpy.data.actions and action_name in bpy.data.actions:
                action = bpy.data.actions[action_name]
                action.name = action_name_new
        self.name_old = self.name
        self.id_data.coa_tools.anim_collections_index = self.id_data.coa_tools.anim_collections_index

    name: StringProperty(update=check_name)
    name_change_to: StringProperty()
    name_old: StringProperty()
    action_collection: BoolProperty(default=False)
    frame_start: IntProperty(default=0, update=set_frame_start)
    frame_end: IntProperty(default=250, min=1, update=set_frame_end)
    timeline_events: CollectionProperty(type=TimelineEvent)
    event_index: IntProperty(default=-1, max=-1)

class ObjectProperties(bpy.types.PropertyGroup):
    anim_collections: bpy.props.CollectionProperty(type=AnimationCollections)
    uv_default_state: bpy.props.CollectionProperty(type=UVData)
    slot: bpy.props.CollectionProperty(type=SlotData)
    blend_mode: bpy.props.EnumProperty(name="Blend Mode", description="Defines the blend mode of a sprite", items=(
        ("BLEND", "Blendmode - Normal", "Normal"), ("ADD", "Blendmode - Add", "Add"), ("MULTIPLY", "Blendmode - Multiply", "Multiply")), update=set_blend_mode)

    dimensions_old: FloatVectorProperty()
    sprite_dimension: FloatVectorProperty()
    z_value: IntProperty(description="Z Depth", default=0, update=set_z_value)
    z_value_last: IntProperty(default=0)
    alpha: FloatProperty(default=1.0, min=0.0, max=1.0, update=set_alpha)
    alpha_last: FloatProperty(default=1.0, min=0.0, max=1.0)
    show_bones: BoolProperty()
    filter_names: StringProperty(update=update_filter, options={'TEXTEDIT_UPDATE'})
    favorite: BoolProperty(default=False)
    hide_base_sprite: BoolProperty(default=False, update=hide_base_sprite)
    animation_loop: BoolProperty(default=False, description="Sets the Timeline frame to 0 when it reaches the end of the animation. Also works for changing frame with cursor keys.")
    hide: BoolProperty(default=False, update=hide)
    hide_select: BoolProperty(default=False, update=hide_select)
    data_path: StringProperty()
    show_children: BoolProperty(default=True)
    show_export_box: BoolProperty()
    sprite_frame_previews: EnumProperty(items=enum_sprite_previews, update=set_sprite_frame)
    sprite_updated: BoolProperty(default=False)
    modulate_color: FloatVectorProperty(name="Modulate Color",
                                                             description="Modulate color for sprites. This will tint your sprite with given color.",
                                                             default=(1.0, 1.0, 1.0), min=0.0, max=1.0, soft_min=0.0,
                                                             soft_max=1.0, size=3, subtype="COLOR",
                                                             update=set_modulate_color)
    modulate_color_last: FloatVectorProperty(default=(1.0, 1.0, 1.0), min=0.0, max=1.0,
                                                                  soft_min=0.0, soft_max=1.0, size=3, subtype="COLOR")
    type: EnumProperty(name="Object Type", default="MESH", items=(
        ("SPRITE", "Sprite", "Sprite"), ("MESH", "Mesh", "Mesh"), ("SLOT", "Slot", "Slot")))
    slot_index: bpy.props.IntProperty(default=0, update=change_slot_mesh, min=0)
    slot_index_last: bpy.props.IntProperty()
    slot_reset_index: bpy.props.IntProperty(default=0, min=0)
    slot_show: bpy.props.BoolProperty(default=False)
    change_z_ordering: bpy.props.BoolProperty(default=False)
    selected_shapekey: bpy.props.EnumProperty(items=get_shapekeys, update=select_shapekey,
                                                                   name="Active Shapkey")

    edit_mode: EnumProperty(name="Edit Mode", items=(
        ("OBJECT", "Object", "Object"), ("MESH", "Mesh", "Mesh"), ("ARMATURE", "Armature", "Armature"),
        ("WEIGHTS", "Weights", "Weights"), ("SHAPEKEY", "Shapkey", "Shapekey")))
    edit_weights: BoolProperty(default=False, update=exit_edit_weights)
    edit_armature: BoolProperty(default=False)
    edit_shapekey: BoolProperty(default=False, update=exit_edit_shapekey)
    edit_mesh: BoolProperty(default=False, update=change_edit_mode)

    anim_collections_index: IntProperty(update=set_actions)

class SceneProperties(bpy.types.PropertyGroup):
    display_all: BoolProperty(default=True)
    display_page: IntProperty(default=0, min=0, name="Display Page", description="Defines which page is displayed")
    display_length: IntProperty(default=10, min=0, name="Page Length", description="Defines how Many Items are displayed")
    distance: FloatProperty(description="Set the asset distance for each Paint Stroke", default=1.0, min=-.0, max=30.0)
    detail: FloatProperty(description="Detail", default=.3, min=0, max=1.0)
    snap_distance: FloatProperty(description="Snap Distance", default=0.01, min=0)
    surface_snap: BoolProperty(default=True, description="Snap Vertices on Surface", update=snapping)
    automerge: BoolProperty(default=False)
    distance_constraint: BoolProperty(default=False, description="Constraint Distance to Viewport", update=update_stroke_distance)
    lock_to_bounds: BoolProperty(default=True, description="Lock Cursor to Object Bounds")
    frame_last: IntProperty(description="Stores last frame Number", default=0)
    view: EnumProperty(default="3D",
                       items=(("3D", "3D View", "3D", "MESH_CUBE", 0), ("2D", "2D View", "2D", "MESH_PLANE", 1)),
                       update=lock_view)
    active_collection: EnumProperty(name="Active Collection", description="Shows content of active collection.", items=get_available_collections)

    nla_mode: EnumProperty(description="Animation Mode. Can be set to NLA or Action to playback all NLA Strips or only Single Actions",items=(("ACTION","ACTION","ACTION","ACTION",0),("NLA","NLA","NLA","NLA",1)),update=set_nla_mode)
    frame_start: IntProperty(name="Frame Start",default=0,min=0,update=update_frame_range)
    frame_end: IntProperty(name="Frame End",default=250,min=1,update=update_frame_range)
    deprecated_data_found: BoolProperty(name="Deprecated Data", default=False)


    # Exporer Properties
    project_name: bpy.props.StringProperty(default="New Project", name="Project name")
    runtime_format: bpy.props.EnumProperty(default="CREATURE", description="Exports for choosen runtime.",items=(("CREATURE","Creature","Creature"),("DRAGONBONES","Dragonbones","Dragonbones")))
    export_path: bpy.props.StringProperty(default="", name="Export Path",subtype="DIR_PATH")
    export_image_mode: bpy.props.EnumProperty(default="ATLAS", name="Image Mode",items=(("ATLAS","Atlas","Atlas"),("IMAGES","Images","Images")))
    atlas_mode: bpy.props.EnumProperty(default="LIMIT_SIZE", name="Atlas Mode",items=(("AUTO_SIZE", "Auto Size", "Auto Size"),("LIMIT_SIZE","Limit Size","Limit Size")))
    sprite_scale: bpy.props.FloatProperty(default=1.0, min=0.1, max=1.0, name="Sprite Output Scale", description="Define the Sprite Output Scale", step=0.1)
    atlas_resolution_x: bpy.props.IntProperty(default=1024,name="Resolution X",min=8,subtype="PIXEL")
    atlas_resolution_y: bpy.props.IntProperty(default=1024, name="Resolution Y",min=8,subtype="PIXEL")
    atlas_island_margin: bpy.props.IntProperty(default=1, name="Texture Island Margin",min=1,subtype="PIXEL")
    export_bake_anim: bpy.props.BoolProperty(default=False, name="Bake Animation")
    export_bake_steps: bpy.props.IntProperty(default=1, min=1, name="Bake Steps",description="Set key every x Frame.")
    minify_json: bpy.props.BoolProperty(default=True, name="Minify Json File", description="Minifies the json file for a fast loading file. Good if used in Web Applications.")
    export_square_atlas: bpy.props.BoolProperty(default=True, name="Force Square Texture Atlas", description="This option makes sure the exported Atlas is always perfectly squared.")
    export_texture_bleed: bpy.props.IntProperty(default=0, min=0, name="Texture Bleeding", subtype="PIXEL", description="Defines how far the texture extends the mesh boundaries.")
    armature_scale: bpy.props.FloatProperty(default=1.0, min=0.1, name="Armature Output Scale", description="Define the Armature Output Scale", step=0.1)

    outliner_filter_names: StringProperty(update=update_filter, options={'TEXTEDIT_UPDATE'})
    outliner_favorites:BoolProperty(default=False)
    outliner: CollectionProperty(type=outliner.COAOutliner)
    outliner_index: IntProperty(update=outliner.select_outliner_object)


class MeshProperties(bpy.types.PropertyGroup):
    hide_base_sprite: BoolProperty(default=False, update=hide_base_sprite,
                                                      description="Make sure to hide base sprite when adding a custom mesh.")

class BoneProperties(bpy.types.PropertyGroup):
    favorite: BoolProperty()
    draw_bone: BoolProperty(default=False)
    z_value: IntProperty(description="Z Depth", default=0)
    data_path: StringProperty()
    hide_select: BoolProperty(default=False, update=hide_select_bone)
    hide: BoolProperty(default=False, update=hide_bone)
    bone_name: StringProperty()
    show_children: BoolProperty(default=False)

class WindowManagerProperties(bpy.types.PropertyGroup):
    show_help: BoolProperty(default=False, description="Hide Help")

def register():
    bpy.types.Object.coa_tools = PointerProperty(type=ObjectProperties)
    bpy.types.Scene.coa_tools = PointerProperty(type=SceneProperties)
    bpy.types.Mesh.coa_tools = PointerProperty(type=MeshProperties)
    bpy.types.Bone.coa_tools = PointerProperty(type=BoneProperties)
    bpy.types.WindowManager.coa_tools = PointerProperty(type=WindowManagerProperties)
    print("COATools Properties have been registered")

def unregister():
    del bpy.types.Object.coa_tools
    del bpy.types.Scene.coa_tools
    del bpy.types.Mesh.coa_tools
    del bpy.types.Bone.coa_tools
