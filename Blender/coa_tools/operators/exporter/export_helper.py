import bpy
import bmesh
from ... functions import *

def property_key_on_frame(obj,prop_names,frame,type="PROPERTY"):
    if type == "SHAPEKEY":
        obj = obj.shape_keys

    if obj != None and obj.animation_data != None:
    ### check if property has a key set
        action = obj.animation_data.action
        if action != None:
            for fcurve in action.fcurves:
                for prop_name in prop_names:
                    if prop_name in fcurve.data_path:
                        for keyframe in fcurve.keyframe_points:
                            if keyframe.co[0] == frame:
                                return True
    ### check if property has a bone driver and bone has a key set
        for driver in obj.animation_data.drivers:
            for prop_name in prop_names:
                if prop_name in driver.data_path:
                    for var in driver.driver.variables:
                        armature = var.targets[0].id
                        if armature != None:
                            bone_target = var.targets[0].bone_target
                            if bone_target in armature.data.bones:
                                bone = armature.data.bones[bone_target]
                                pbone = armature.pose.bones[bone_target]
                                key_on_frame = bone_key_on_frame(bone,frame,armature.animation_data,type="ANY")
                                if key_on_frame:
                                    return key_on_frame
                                for const in pbone.constraints:
                                    if const.type == "ACTION":
                                        bone = armature.data.bones[const.subtarget] if const.subtarget in armature.data.bones else None
                                        if bone != None:
                                            key_on_frame = bone_key_on_frame(bone,frame,armature.animation_data,type="ANY")
                                        if key_on_frame:
                                            return key_on_frame
    return False

def remove_base_sprite(obj):
    active_object = bpy.context.active_object
    for modifier in obj.modifiers:
        if modifier.name == "coa_base_sprite":
            obj.modifiers.remove(modifier)
    bpy.context.view_layer.objects.active = obj
    obj.hide_set(False)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    verts = []

    if "coa_base_sprite" in obj.vertex_groups and obj.data.coa_tools.hide_base_sprite:
        v_group_idx = obj.vertex_groups["coa_base_sprite"].index
        for i,vert in enumerate(obj.data.vertices):
            for g in vert.groups:
                if g.group == v_group_idx and g.weight > 0:
                    verts.append(bm.verts[i])
                    break

    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')


    bmesh.ops.delete(bm,geom=verts,context="VERTS")
    bm = bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = active_object