import bpy
import os


class COATOOLS_OT_VersionConverter(bpy.types.Operator):
    bl_idname = "coa_tools.convert_deprecated_data"
    bl_label = "Convert COA Data(2.79 to 2.80)"
    bl_description = "Convert blendfile from 2.79 to 2.80"
    bl_options = {"REGISTER"}


    @classmethod
    def poll(cls, context):
        return True

    def convert_actions(self, old_name, new_name):
        for action in bpy.data.actions:
            if old_name in action.name:
                action.name = action.name.split(old_name)[0]+new_name

    def convert_sprite_objects(self):
        # converts empty sprite objects to armature sprite objects
        converted_sprite_objects = []
        old_name = ""
        new_name = ""

        for obj in bpy.data.objects:
            obj_name = obj.name
            if "sprite_object" in obj.coa_tools and obj.type != "ARMATURE" and obj not in converted_sprite_objects:
                armature = None
                for child in obj.children:
                    if child.type == "ARMATURE":
                        armature = child
                        armature.coa_tools["sprite_object"] = True
                        armature["coa_tools"] = obj["coa_tools"]
                        break
                for child in obj.children:
                    if child != armature:
                        child.parent = armature

                bpy.data.objects.remove(obj)
                if armature != None:
                    old_name = str(armature.name)
                    new_name = str(obj_name)
                    armature.name = obj_name
        if old_name != new_name:
            self.convert_actions(old_name, new_name)
        bpy.context.evaluated_depsgraph_get()
    def convert_properties(self):
        # convert meshes
        for mesh in bpy.data.meshes:
            for prop_name in mesh.keys():
                if "coa_" in prop_name and "coa_tools" not in prop_name:
                    prop_name_new = prop_name.split("coa_")[1]
                    mesh.coa_tools[prop_name_new] = mesh[prop_name]
                    

        # convert objects
        for obj in bpy.data.objects:
            #for prop_name in obj.keys():
                

            if "sprite_object" in obj:
                obj.coa_tools["sprite_object"] = True
                del obj["sprite_object"]
            for prop_name in obj.keys():
                if "coa_" in prop_name and "coa_tools" not in prop_name:
                    prop_name_new = prop_name.split("coa_")[1]
                    obj.coa_tools[prop_name_new] = obj[prop_name]

                    anim = obj.animation_data
                    if anim is not None and anim.action is not None:
                        for fcu in anim.action.fcurves:
                            if(str(fcu.data_path)==prop_name):
                                anim.action.fcurves.remove(fcu)

                    if prop_name=="coa_anim_collections":
                        cAc=0
                        for ac in obj[prop_name]:
                            for ac_name in ac.keys():
                                if(ac_name=="event"):
                                    cEv=0
                                    obj.coa_tools[prop_name_new][cAc]["timeline_events"]=[]
                                    replaceArray=[]
                                    for ev_name in ac[ac_name]:
         

                                        tempColl={}
                                        print(str(ev_name["frame"]))
                                        tempColl["frame"]=int(ev_name["frame"])
                                        tempColl["event"]=[{},{}]
                                        ev_index=0
                                        if("sound" in ev_name.keys()):
                                            if ev_name["sound"]!="":
                                                tempColl["event"][ev_index]["type"]="SOUND"
                                                tempColl["event"][ev_index]["value"]=ev_name["sound"]
                                                ev_index+=1
                                        if("action" in ev_name.keys()):
                                            if ev_name["action"]!="":
                                                tempColl["event"][ev_index]["type"]="EVENT"
                                                tempColl["event"][ev_index]["value"]=ev_name["action"]
                                                ev_index+=1
                                        replaceArray.append(tempColl)
                                        #print(str(ev_name["sound"]))

                                        cEv+=1
                                    obj.coa_tools[prop_name_new][cAc]["timeline_events"]=replaceArray
                            cAc+=1
                    del obj[prop_name]


    def clear_material(self, mat):
        mat.use_nodes = True
        # cleanup node tree
        for node in mat.node_tree.nodes:
            if node.type != "OUTPUT_MATERIAL":
                mat.node_tree.nodes.remove(node)
            else:
                output_node = node
        return mat

    def setup_material(self, context, mesh, mat, texture_name):
        # mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        node_tree = mat.node_tree
        output_node = None
        # # cleanup node tree
        for node in mat.node_tree.nodes:
            if node.type == "OUTPUT_MATERIAL":
                output_node = node
        # create all required nodes and connect them
        tex_node = node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.interpolation = "Closest"
        if texture_name in bpy.data.images:
            tex_node.image = bpy.data.images[texture_name]

        bpy.ops.coa_tools.create_material_group()
        coa_node_tree = bpy.data.node_groups["COATools Material"]
        coa_node = node_tree.nodes.new("ShaderNodeGroup")
        coa_node.name = "COA Material"
        coa_node.label = "COA Material"
        coa_node.node_tree = coa_node_tree
        coa_node.inputs["Alpha"].default_value = 1.0
        coa_node.inputs["Modulate Color"].default_value = [1, 1, 1, 1]

        node_tree.links.new(coa_node.inputs["Texture Color"], tex_node.outputs["Color"], verify_limits=True)
        node_tree.links.new(coa_node.inputs["Texture Alpha"], tex_node.outputs["Alpha"], verify_limits=True)
        node_tree.links.new(coa_node.outputs["BSDF"], output_node.inputs["Surface"], verify_limits=True)

        # position nodes in node tree
        tex_node.location = (0, 0)
        coa_node.location = (280, 0)
        output_node.location = (460, 0)
        mesh.materials.append(mat)
        return mat

    def convert_materials(self, context):
        texture_dir_path = os.path.join(os.path.dirname(bpy.data.filepath), "sprites")
        bpy.ops.coa_tools.create_material_group()
        meshes = []
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                if obj.coa_tools.type == "MESH":
                    if obj.data not in meshes:
                        meshes.append(obj.data)
                elif obj.coa_tools.type == "SLOT":
                    for slot in obj.coa_tools.slot:
                        if slot.mesh not in meshes:
                            meshes.append(slot.mesh)

        for mesh in meshes:
            for material_name in mesh.materials.keys():
                mat = mesh.materials[material_name] if material_name in mesh.materials else None
                if mat != None:
                    texture_name = None
                    if mat.use_nodes and mat.node_tree != None:
                        for node in mat.node_tree.nodes:
                            if node.type == "TEX_IMAGE" and node.image is not None:
                                texture_name = node.image.name
                                break

                    if texture_name != None:
                        mesh.materials.clear()
                        self.setup_material(context, mesh, self.clear_material(mat), texture_name)
                    else:
                        self.setup_material(context, mesh, self.clear_material(mat), material_name)


    def convert_drivers(self, context):
        for obj in bpy.data.objects:
            if obj.animation_data != None:
                anim_data = obj.animation_data
                for driver in anim_data.drivers:
                    if "coa_" in driver.data_path and not "coa_tools." in driver.data_path:
                        driver.data_path = "coa_tools." + driver.data_path.split("coa_")[1]

                        # Update Driver dependencies by setting expression value and resetting
                        driver.driver.expression += " "
                        driver.driver.expression = driver.driver.expression[:-1]

    def set_shading(self):
        bpy.context.scene.view_settings.view_transform = "Standard"
        for obj in bpy.data.objects:
            if "sprite_object" in obj.coa_tools:
                for screen in bpy.data.screens:
                    for area in screen.areas:
                        if area.type == "VIEW_3D":
                            area.spaces[0].shading.type = "SOLID"
                            area.spaces[0].shading.light = "FLAT"
                break

    def execute(self, context):
        self.convert_properties()
        self.convert_materials(context)
        self.convert_drivers(context)
        self.convert_sprite_objects()
        self.set_shading()
        context.scene.coa_tools.deprecated_data_found = False
        return {"FINISHED"}