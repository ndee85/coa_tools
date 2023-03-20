import bpy
from .. functions import *


class COATOOLS_OT_ConvertMaterials(bpy.types.Operator):
    bl_idname = "coa_tools.convert_bi_to_cycles_materials"
    bl_label = "Convert BI to Cycles Materials"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def convert_bi_mat_to_cycles_mat(self,obj):
        for slot in obj.material_slots:
            mat = slot.material
            
            if mat != None:
                mat_c = bpy.data.materials.new(mat.name+"_c")
                mat_c.use_nodes = True
                mat_c.game_settings.alpha_blend = "ALPHA"
                node_tree = mat_c.node_tree
                
                for node in node_tree.nodes:
                    node_tree.nodes.remove(node)
                
                ### get texture of material
                img = None
                for tex_slot in mat.texture_slots:
                    if tex_slot != None and tex_slot.texture != None:
                        tex = tex_slot.texture
                        if tex.image != None:
                            img = tex.image
                            break
                
                ### create nodes
                node_rgb = node_tree.nodes.new("ShaderNodeRGB")
                node_texture = node_tree.nodes.new("ShaderNodeTexImage")
                node_mix = node_tree.nodes.new("ShaderNodeMixRGB")
                node_math = node_tree.nodes.new("ShaderNodeMath")
                node_shader_transp = node_tree.nodes.new("ShaderNodeBsdfTransparent")
                node_shader_emission = node_tree.nodes.new("ShaderNodeEmission")
                node_shader_mix = node_tree.nodes.new("ShaderNodeMixShader")
                node_output = node_tree.nodes.new("ShaderNodeOutputMaterial")
                
                ### set extra properties to make them identifiable
                node_rgb["coa_modulate_color"] = True
                node_math["coa_alpha"] = True
                
                ### position nodes
                node_rgb.location = [-400,320]
                node_texture.location = [-400,100]
                node_mix.location = [-200,240]
                node_math.location = [-200,40]
                node_shader_transp.location = [0,140]
                node_shader_emission.location = [0,40]
                node_shader_mix.location = [200,120]
                node_output.location = [380,120]
                
                ### wire up nodes
                node_tree.links.new(node_mix.inputs[2], node_rgb.outputs[0])
                node_tree.links.new(node_mix.inputs[1], node_texture.outputs[0])
                node_tree.links.new(node_math.inputs[0], node_texture.outputs[1])
                node_tree.links.new(node_shader_transp.inputs[0], node_mix.outputs[0])
                node_tree.links.new(node_shader_emission.inputs[0], node_mix.outputs[0])
                node_tree.links.new(node_shader_mix.inputs[0], node_math.outputs[0])
                node_tree.links.new(node_shader_mix.inputs[1], node_shader_transp.outputs[0])
                node_tree.links.new(node_shader_mix.inputs[2], node_shader_emission.outputs[0])
                node_tree.links.new(node_output.inputs[0], node_shader_mix.outputs[0])
                
                ### setup nodes
                node_rgb.outputs[0].default_value[:3] = obj.coa_modulate_color
                node_texture.image = img
                node_mix.blend_type = "MULTIPLY"
                node_mix.inputs[0].default_value = 1.0
                node_math.operation = "MULTIPLY"
                node_math.inputs[1].default_value = 1.0
                
                slot.material = mat_c

        
            

    def execute(self, context):
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        children = get_children(context,sprite_object,ob_list=[])
        
        
        for child in children:
            if child.type == "MESH":
                self.convert_bi_mat_to_cycles_mat(child)
        
        return {"FINISHED"}
        