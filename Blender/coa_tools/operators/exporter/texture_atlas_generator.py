import bpy
from mathutils import Vector
from mathutils.geometry import intersect_line_line_2d
import math
from ... import constants


class TextureData:
    def __init__(self, img_name, texture_object, bounds_px, bounds_rel, width, height):
        self.img_name = img_name
        self.texture_object = texture_object
        self.bounds_px = bounds_px
        self.bounds_rel = bounds_rel
        self.width = width
        self.height = height


class TextureSlot:
    def __init__(self, x, y, texture_data):
        self.x = x
        self.y = y
        self.texture_data = texture_data


class TextureAtlas:
    def __init__(self, name, width, height, max_width, max_height, margin=1, square=True, output_scale=1.0):
        self.name = name
        self.width = width
        self.height = height
        self.max_width = max_width
        self.max_height = max_height
        self.margin = margin
        self.square = square
        self.texture_slots = []
        self.create_new_slot(self.margin, self.margin)
        self.output_scale = output_scale

    def create_new_slot(self, x, y):
        texture_slot = TextureSlot(x, y, None)
        self.texture_slots.append(texture_slot)
        self.texture_slots = sorted(self.texture_slots, key=lambda slot: slot.x, reverse=True)
        self.texture_slots = sorted(self.texture_slots, key=lambda slot: slot.y, reverse=False)
        return texture_slot

    def cleanup_slots(self):
        del self.texture_slots[:]
        self.create_new_slot(self.margin, self.margin)


def transfer_alpha(diffuse_img, alpha_img):
    diffuse_pixels = list(diffuse_img.pixels)
    alpha_pixels = list(alpha_img.pixels)

    for i in range(0, len(alpha_pixels), 4):
        diffuse_pixels[i + 3] = alpha_pixels[i]

    diffuse_img.pixels[:] = diffuse_pixels
    diffuse_img.update()

def convert_to_straight_alpha(img):
    pixels = list(img.pixels)

    for i in range(0, len(pixels), 4):
        a = pixels[i+3]
        if a > 0:
            pixels[i] = pixels[i] / a
            pixels[i+1] = pixels[i+1] / a
            pixels[i+2] = pixels[i+2] / a
    img.pixels[:] = pixels
    img.update()

class TextureAtlasGenerator:
    @staticmethod
    def get_texture_bounds(obj, output_scale):
        uvs = obj.data.uv_layers[0].data
        textures = obj.data.uv_layers[0].data

        image = None

        for node in obj.active_material.node_tree.nodes:
            if node.type == "GROUP" and node.node_tree.name == constants.COA_NODE_GROUP_NAME:
                links = node.inputs[0].links
                image = links[0].from_node.image if len(links) > 0 else None

        if image != None:
            img_size = image.size
            bottom_left_x = 1.0
            bottom_left_y = 1.0
            top_right_x = 0.0
            top_right_y = 0.0
            for uv in uvs:
                bottom_left_x = min(bottom_left_x, uv.uv[0])
                bottom_left_y = min(bottom_left_y, uv.uv[1])
                top_right_x = max(top_right_x, uv.uv[0])
                top_right_y = max(top_right_y, uv.uv[1])

            bounds_rel = [bottom_left_x, bottom_left_y, top_right_x, top_right_y]
            bounds_px = [img_size[0] * bottom_left_x, img_size[1] * bottom_left_y, img_size[0] * top_right_x,
                         img_size[1] * top_right_y]

            for i, value in enumerate(bounds_px):
                bounds_px[i] = int(bounds_px[i] * output_scale)
            width = abs((bounds_px[2] - bounds_px[0]))
            height = abs((bounds_px[3] - bounds_px[1]))
            texture_data = TextureData(image.name, obj, bounds_px, bounds_rel, width, height)
            return texture_data
        return TextureData(None, obj, [0, 0, 1, 1], [0, 0, 1, 1], 1, 1)

    @staticmethod
    def get_sorted_texture_data(objs, output_scale):
        texture_data_list = []
        for obj in objs:
            if obj.type == "MESH":
                texture_data = TextureAtlasGenerator.get_texture_bounds(obj, output_scale)
                if texture_data != None:
                    texture_data_list.append(texture_data)

        texture_data_list = sorted(texture_data_list,
                                   key=lambda x: x.width * x.height + math.pow(x.width, 1) + math.pow(x.height, 1),
                                   reverse=True)
        return texture_data_list

    @staticmethod
    def texture_intersects_others(texture_data, texture_slot, atlas_data):
        tex_fits_width = texture_slot.x + (texture_data.width + atlas_data.margin) < atlas_data.width
        tex_fits_height = texture_slot.y + (texture_data.height + atlas_data.margin) < atlas_data.height
        if tex_fits_width == False or tex_fits_height == False:
            return True
        for slot in atlas_data.texture_slots:
            if slot.texture_data != None and slot != texture_slot:

                r1 = []
                r1.append(texture_slot.x)
                r1.append(texture_slot.y)
                r1.append(texture_slot.x + texture_data.width)
                r1.append(texture_slot.y + texture_data.height)
                r2 = []
                r2.append(slot.x)
                r2.append(slot.y)
                r2.append(slot.x + slot.texture_data.width)
                r2.append(slot.y + slot.texture_data.height)

                points_a = []
                points_a.append(Vector((r1[0], r1[1])))
                points_a.append(Vector((r1[2], r1[1])))
                points_a.append(Vector((r1[2], r1[3])))
                points_a.append(Vector((r1[0], r1[3])))
                lines_a = [[points_a[0], points_a[1]], [points_a[1], points_a[2]], [points_a[2], points_a[3]],
                           [points_a[3], points_a[0]]]

                points_b = []
                points_b.append(Vector((r2[0], r2[1])))
                points_b.append(Vector((r2[2], r2[1])))
                points_b.append(Vector((r2[2], r2[3])))
                points_b.append(Vector((r2[0], r2[3])))
                lines_b = [[points_b[0], points_b[1]], [points_b[1], points_b[2]], [points_b[2], points_b[3]],
                           [points_b[3], points_b[0]]]

                for line_a in lines_a:
                    for line_b in lines_b:
                        i = intersect_line_line_2d(line_a[0], line_a[1], line_b[0], line_b[1])
                        if i != None:
                            return True

        return False

    @staticmethod
    def create_texture_atlas_data(texture_data_list, atlas_name, width, height, max_width, max_height, margin=0,
                                  square=True, output_scale=1.0):
        atlas_data = TextureAtlas(atlas_name, width, height, max_width, max_height, margin, square, output_scale)
        objects = []
        for texture_data in texture_data_list:
            objects.append(texture_data.texture_object)

        restart_generation = True
        decrease_scale = False
        while restart_generation == True:

            if restart_generation == True:
                if decrease_scale:
                    atlas_data.output_scale *= 0.95
                    decrease_scale = False
                texture_data_list = TextureAtlasGenerator.get_sorted_texture_data(objects, atlas_data.output_scale)
                atlas_data.cleanup_slots()
                restart_generation = False

            for i, texture_data in enumerate(texture_data_list):
                if restart_generation:
                    break
                for j, texture_slot in enumerate(atlas_data.texture_slots):
                    if texture_slot.texture_data == None:
                        tex_intersects_other = TextureAtlasGenerator.texture_intersects_others(texture_data,
                                                                                               texture_slot, atlas_data)
                        if tex_intersects_other and j == len(atlas_data.texture_slots) - 1:
                            if atlas_data.width == atlas_data.height and atlas_data.height < atlas_data.max_height:
                                atlas_data.height *= 2
                                if atlas_data.square:
                                    if atlas_data.width < atlas_data.height:
                                        atlas_data.width *= 2
                            elif atlas_data.height > atlas_data.width and atlas_data.width < atlas_data.max_width:
                                atlas_data.width *= 2

                            if atlas_data.width >= atlas_data.max_width and atlas_data.height >= atlas_data.max_height:
                                decrease_scale = True
                                print("Max Atlas size of ", atlas_data.width, "x", atlas_data.height,
                                      " reached. Decreasing texture size and restarting generation.")
                            else:
                                print("Current Atlas size is to small. Increasing to", atlas_data.width, "x", atlas_data.height,
                                      " and restarting generation.")
                            restart_generation = True

                        if restart_generation:
                            break
                        if not tex_intersects_other:
                            texture_slot.texture_data = texture_data
                            x1 = texture_slot.x + texture_data.width
                            y1 = texture_slot.y
                            x2 = texture_slot.x
                            y2 = texture_slot.y + texture_data.height
                            atlas_data.create_new_slot(x1 + margin, y1)
                            atlas_data.create_new_slot(x2, y2 + margin)
                            break

        return atlas_data

    @staticmethod
    def create_bake_node(merged_uv_obj, bake_img):
        for mat in merged_uv_obj.data.materials:
            for node in mat.node_tree.nodes:
                node.select = False

                if node.type == "GROUP" and node.node_tree.name == constants.COA_NODE_GROUP_NAME:
                    links = node.inputs[0].links
                    tex_node = links[0].from_node if len(links) > 0 else None
                    if tex_node != None and tex_node.type == 'TEX_IMAGE':
                        tex_node.interpolation = "Linear"

            if "COA Bake Node" not in mat.node_tree.nodes:
                bake_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            else:
                bake_node = mat.node_tree.nodes["COA Bake Node"]
            bake_node.name = "COA Bake Node"
            bake_node.select = True
            bake_node.location = [400, 0]
            mat.node_tree.nodes.active = bake_node
            bake_node.image = bake_img
            bake_node.interpolation = "Linear"

    @staticmethod
    def setup_alpha_bake(merged_uv_obj):
        for mat in merged_uv_obj.data.materials:
            for node in mat.node_tree.nodes:
                if node.type == "GROUP" and node.node_tree.name == constants.COA_NODE_GROUP_NAME:
                    links = node.inputs[1].links
                    tex_node = links[0].from_node if len(links) > 0 else None
                    if tex_node != None:
                        mat.node_tree.links.new(tex_node.outputs[1], node.inputs[0])
                    elif node.inputs[0].links[0] != None:
                        value_node = mat.node_tree.nodes.new('ShaderNodeValue')
                        value_node.outputs[0].default_value = node.inputs[1].default_value
                        mat.node_tree.links.new(value_node.outputs[0], node.inputs[0])

    @staticmethod
    def generate_uv_layout(name="texture_atlas", objects=None, width=256, height=256, max_width=2048, max_height=2048,
                           margin=1, texture_bleed=0, square=True, output_scale=1.0):
        context = bpy.context

        ### Create new Collection for Rendering
        for collection in context.scene.collection.children:
            collection.hide_render = True

        render_collection = bpy.data.collections.new("COA Atlas Collection")
        context.scene.collection.children.link(render_collection)
        render_collection.hide_render = False
        if("COA Export Collection" in bpy.data.collections):
            bpy.data.collections["COA Export Collection"].hide_render = True

        ### Extract texture data from given objects. Gives texture width, height and boundaries
        texture_data_list = TextureAtlasGenerator.get_sorted_texture_data(objects, output_scale)


        ### Generates Atlas data which is later used to create uv data
        atlas_data = TextureAtlasGenerator.create_texture_atlas_data(texture_data_list, name, width, height, max_width,
                                                                     max_height, margin, square, output_scale)

        ### create new object with atlas uv layout
        slot_len = 0
        uv_objs = []
        atlas_objs = []
        for slot in atlas_data.texture_slots:
            # if slot.texture_data != None and slot.texture_data.img_name == None:
            #     obj = slot.texture_data.texture_object
            #     uv_objs.append(obj)
            if slot.texture_data != None:# and slot.texture_data.img_name != None:
                slot_len += 1
                obj = slot.texture_data.texture_object
                uv_objs.append(obj)
                uv_map = obj.data.uv_layers.new(name="COA_UV_ATLAS")
                uv_layer = obj.data.uv_layers["COA_UV_ATLAS"]

                uv_old_width = slot.texture_data.bounds_rel[2] - slot.texture_data.bounds_rel[0]
                uv_old_height = slot.texture_data.bounds_rel[3] - slot.texture_data.bounds_rel[1]
                uv_old_pos = Vector((slot.texture_data.bounds_rel[0], slot.texture_data.bounds_rel[1]))

                uv_new_width = slot.texture_data.width / atlas_data.width
                uv_new_height = slot.texture_data.height / atlas_data.height
                uv_new_pos = Vector((slot.x / atlas_data.width, slot.y / atlas_data.height))

                scale_x = uv_new_width / uv_old_width
                scale_y = uv_new_height / uv_old_height

                uv_flip_y = (1.0 - uv_new_height) - 2 * (uv_new_pos.y)

                for uv_data in uv_layer.data:
                    uv = uv_data.uv
                    uv -= uv_old_pos
                    uv[0] *= scale_x
                    uv[1] *= scale_y
                    uv += uv_new_pos
                    uv_data.uv += Vector((0, uv_flip_y))

                # copy atlas objects and position them properly for rendering
                atlas_obj = obj.copy()
                atlas_obj.data = atlas_obj.data.copy()
                render_collection.objects.link(atlas_obj)
                atlas_objs.append(atlas_obj)
                atlas_obj.coa_tools.driver_remove("alpha")
                atlas_obj.coa_tools.alpha = 1.0

                obj_scale_x = (atlas_obj.dimensions[0]/atlas_obj.scale[0]) / slot.texture_data.width
                obj_scale_y = (atlas_obj.dimensions[2]/atlas_obj.scale[2]) / slot.texture_data.height
                atlas_obj.location = [slot.x, 0, -slot.y]
                atlas_obj.scale[0] = 1.0/obj_scale_x
                atlas_obj.scale[2] = 1.0/obj_scale_y
                x = math.inf
                y = -math.inf
                verts = atlas_obj.data.vertices
                if atlas_obj.data.shape_keys is not None and len(atlas_obj.data.shape_keys.key_blocks) > 0:
                    verts = atlas_obj.data.shape_keys.key_blocks[0].data
                for vert in verts:
                    if vert.co[0] < x:
                        x = vert.co[0]
                    if vert.co[2] > y:
                        y = vert.co[2]
                for vert in verts:
                    vert.co[0] -= x
                    vert.co[2] -= y

        # add render camera and setup render settings
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        render_collection.objects.link(cam)
        cam.data.type = "ORTHO"
        cam.location[0] = atlas_data.width * .5
        cam.location[2] = -atlas_data.height * .5
        cam.location[1] = -10
        cam.rotation_euler[0] = math.pi * .5
        cam.data.ortho_scale = max(atlas_data.width, atlas_data.height)
        context.scene.render.image_settings.compression = 0#85
        context.scene.render.resolution_x = atlas_data.width
        context.scene.eevee.taa_render_samples = 16
        context.scene.render.resolution_y = atlas_data.height
        context.scene.render.film_transparent = True
        context.scene.render.engine = "BLENDER_EEVEE"
        context.scene.render.filter_size = 1.0
        context.scene.camera = cam
        context.scene.world.color = [0, 0, 0]
        context.scene.world.use_nodes = False
        bpy.ops.render.render()
        atlas_img = bpy.data.images["Render Result"]

        # merge uv objects into one
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in uv_objs:
            obj.select_set(True)
        context.view_layer.objects.active = uv_objs[0]

        if len(context.selected_objects) > 1:
            bpy.ops.object.join()

        merged_uv_obj = bpy.data.objects[context.active_object.name]
        merged_uv_obj.data.uv_layers.active = merged_uv_obj.data.uv_layers["COA_UV_ATLAS"]
        for vert in merged_uv_obj.data.vertices:
            vert.select = True
            vert.hide = False
        if("COA Export Collection" in bpy.data.collections):
            bpy.data.collections["COA Export Collection"].hide_render = False
        return atlas_img, merged_uv_obj, atlas_data


# TextureAtlasGenerator.generate_uv_layout(name="texture_atlas", objects=bpy.context.selected_objects, width=256,height=256, max_width=1024, max_height=1024, margin=1, texture_bleed=0,square=True, output_scale=1.0)
