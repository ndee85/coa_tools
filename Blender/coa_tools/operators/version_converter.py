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


    def convert_sprite_objects(self):
        # converts empty sprite objects to armature sprite objects
        converted_sprite_objects = []
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
                armature.name = obj_name

    def convert_properties(self):
        # convert meshes
        for mesh in bpy.data.meshes:
            for prop_name in mesh.keys():
                if "coa_" in prop_name and "coa_tools" not in prop_name:
                    prop_name_new = prop_name.split("coa_")[1]
                    mesh.coa_tools[prop_name_new] = mesh[prop_name]

        # convert objects
        for obj in bpy.data.objects:

            if "sprite_object" in obj:
                obj.coa_tools["sprite_object"] = True
                del obj["sprite_object"]
            for prop_name in obj.keys():
                if "coa_" in prop_name and "coa_tools" not in prop_name:
                    prop_name_new = prop_name.split("coa_")[1]
                    obj.coa_tools[prop_name_new] = obj[prop_name]
                    del obj[prop_name]

    def create_material(self, context, mesh, name="Sprite"):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        node_tree = mat.node_tree
        output_node = None
        # cleanup node tree
        for node in mat.node_tree.nodes:
            if node.type != "OUTPUT_MATERIAL":
                mat.node_tree.nodes.remove(node)
            else:
                output_node = node
        # create all required nodes and connect them
        tex_node = node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.interpolation = "Closest"
        if name in bpy.data.images:
            tex_node.image = bpy.data.images[name]

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
                mat = mesh.materials[material_name]
                texture_path = os.path.join(texture_dir_path, material_name)
                if os.path.isfile(texture_path):
                    bpy.data.images.load(texture_path, check_existing=True)
                    bpy.data.materials.remove(mat, do_unlink=True, do_id_user=True, do_ui_user=True)
                    mesh.materials.clear()
                    self.create_material(context, mesh, material_name)
                elif material_name in bpy.data.images:
                    bpy.data.materials.remove(mat, do_unlink=True, do_id_user=True, do_ui_user=True)
                    mesh.materials.clear()
                    self.create_material(context, mesh, material_name)

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
                            area.spaces[0].shading.type = "RENDERED"
                break

    def execute(self, context):
        self.convert_properties()
        self.convert_materials(context)
        self.convert_drivers(context)
        self.convert_sprite_objects()
        self.set_shading()
        context.scene.coa_tools.deprecated_data_found = False
        return {"FINISHED"}