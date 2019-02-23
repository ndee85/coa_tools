#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# CoaTools Exporter
#  by Ragnar Brynjúlfsson
#
# DESCRIPTION
#   CoaTools Exporter is a plug-in for GIMP to export layered cut-out animation
#   object or characters to Cutout Animation Tools: 2D Animation Tools for Blender
#   (see https://github.com/ndee85/coa_tools)
#
# INSTALLATION
#   Drop the script in your plug-ins folder. On Linux this is ~/.gimp-2.8/plug-ins/
#
# VERSION
version = "0.0.0"
# AUTHOR
author = [ 'Ragnar Brynjúlfsson <me@ragnarb.com>', ' ']
# COPYRIGHT
copyright = "Copyright 2016 © Ragnar Brynjúlfsson"
# WEBSITE
website = "https://github.com/ndee85/coa_tools"
plugin = "CoaTools Exporter"
# LICENSE
license = """
CoaTools Exporter
Copyright 2016 Ragnar Brynjúlfsson

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
"""

import os
import json
from math import floor, sqrt, ceil
from gimpfu import *


class Sprite():
    ''' Store file and transform data for each sprite '''

    def __init__(self, name):
        self.name = name
        self.path = 'sprites/{name}'.format(name=self.name)
        self.offset = [0.0, 0.0]
        self.position = [0.0, 0.0]
        self.opacity = 1.0
        self.z = 0
        self.tiles_x = 1
        self.tiles_y = 1

    def get_data(self):
        ''' Return sprite info as json encodable data '''
        data = {
            "name": self.name,
            "type": "SPRITE",
            "resource_path": self.resource_path,
            "vector_path": self.vector_path,
            "node_path": self.name,
            "pivot_offset": [0.0, 0.0],
            "offset": self.offset,
            "position": self.position,
            "rotation": 0.0,
            "scale": [1.0, 1.0],
            "opacity": self.opacity,
            "z": self.z,
            "tiles_x": self.tiles_x,
            "tiles_y": self.tiles_y,
            "frame_index": 0,
            "children": []
        }
        return data


class CoaExport():
    def __init__(self, img, path, name):
        if path and name:
            self.name = name
            self.path = path
            self.original_img = img
            self.offset = [
                img.width / 2 * -1,
                img.height / 2
            ]
            self.sprites = []
            self.json = os.path.join(self.path, self.name, '{name}.json'.format(name=self.name))
            self.sprite_path = os.path.join(self.path, self.name, 'sprites')
            self.vector_path = os.path.join(self.path, self.name, 'paths')
            self.export()

    def paste_layer(self, img, name, x, y):
        ''' Paste a layer with offset '''
        layer = img.new_layer(name,
                                 img.width,
                                 img.height)
        floating_layer = pdb.gimp_edit_paste(layer, True)
        pdb.gimp_floating_sel_anchor(floating_layer)
        self.crop_alpha_from_layer(img, layer)
        pdb.gimp_layer_set_offsets(layer, x, y)

    def export(self):
        ''' Export visible layers and layer groups to CoaSprite '''
        if os.path.isfile(os.path.join(self.path, self.name)):
            show_error_msg('ABORTING!\nDestination is not a folder.\n {path}/{name}'.format(path=self.path, name=self.name))
            return
        if not os.access(self.path, os.W_OK):
            show_error_msg('ABORTING!\nDestination is not a writable.\n {path}'.format(path=self.path))
            return
        if os.path.isdir(os.path.join(self.path, self.name)):
            show_error_msg('Destination exists, I may have overwritten something in {path}/{name}'.format(path=self.path, name=self.name))
        self.mkdir()
        # Loop through visible layers
        self.img = self.original_img.duplicate()
        self.img.undo_group_start()
        for layer in self.img.layers:
            if layer.visible:
                pdb.gimp_image_set_active_layer(self.img, layer)
                # Crop and the layer position
                self.crop_alpha_from_layer(self.img, layer, False)
                self.selection_to_path(self.img, layer)
                z = 0 - pdb.gimp_image_get_item_position(self.img, layer)
                if isinstance(layer, gimp.GroupLayer):
                    if len(layer.children) > 0:
                        self.sprites.append(self.export_sprite_sheet(layer, layer.offsets, z))
                else:
                    self.sprites.append(self.export_sprite(layer, layer.offsets, z))
        for vector in self.img.vectors:
            self.export_vector(self.img, vector)
        self.write_json()
        self.img.undo_group_end()
        pdb.gimp_image_delete(self.img)

    def export_sprite(self, layer, position, z):
        ''' Export single layer to png '''
        name = '{name}.png'.format(name=layer.name)
        svg_name = '{name}.svg'.format(name=layer.name)
        pdb.gimp_edit_copy(layer)
        imgtmp = pdb.gimp_edit_paste_as_new()
        sprite_path = os.path.join(self.sprite_path, name)
        self.save_png(imgtmp, sprite_path)
        pdb.gimp_image_delete(imgtmp)
        # Return sprite object with relevant data
        sprite = Sprite(name)
        sprite.resource_path = 'sprites/{name}'.format(name=name)
        sprite.vector_path = 'paths/{svg_name}'.format(svg_name=svg_name)
        sprite.offset = self.offset
        sprite.position = position
        sprite.opacity = layer.opacity / 100
        sprite.z = z
        return sprite

    def export_vector(self, img, vector):
        name = '{name}.svg'.format(name=vector.name)
        vector_path = os.path.join(self.vector_path, name)
        pdb.gimp_vectors_export_to_file(img, vector_path, vector)

    def export_sprite_sheet(self, layer, position, z):
        ''' Export layer group to a sprite sheet '''
        # Find grid size
        #frames = len(layer.children)
        frames = 0
        for child in layer.children:
            if child.visible and not isinstance(child, gimp.GroupLayer):
                frames = frames + 1
        gridx = floor(sqrt(frames))
        gridy = ceil(frames / gridx)
        self.crop_alpha_from_layer(self.img, layer)
        img2 = gimp.Image(int(layer.width * gridx), int(layer.height * gridy))
        img2.new_layer('background', img2.width, img2.height)
        col = 1
        row = 1
        name = '{name}.png'.format(name=layer.name)
        svg_name = '{name}.svg'.format(name=layer.name)
        # Looop through child layers in the layer group
        for child in layer.children:
            if child.visible and not isinstance(child, gimp.GroupLayer):
                pdb.gimp_image_set_active_layer(self.img, child)
                self.crop_alpha_from_layer(self.img, child)
                x_delta = child.offsets[0] - layer.offsets[0]
                y_delta = child.offsets[1] - layer.offsets[1]
                pdb.gimp_edit_copy(child)
                self.paste_layer(img2,
                                 '{name}_{col}_{row}'.format(name=child.name, col=col, row=row),
                                 (layer.width * (col - 1)) + x_delta,
                                 (layer.height * (row - 1)) + y_delta)
                if col % gridx > 0:
                    col = col + 1
                else:
                    col = 1
                    row = row + 1
        # Flatten and save
        flat_layer = pdb.gimp_image_merge_visible_layers(img2, 0)
        sprite_path = os.path.join(self.sprite_path, name)
        self.save_png(img2, sprite_path)
        pdb.gimp_image_delete(img2)
        # Return sprite object with relevant data
        sprite = Sprite(name)
        sprite.resource_path = 'sprites/{name}'.format(name=name)
        sprite.vector_path = 'paths/{svg_name}'.format(svg_name=svg_name)
        sprite.offset = self.offset
        sprite.position = position
        sprite.opacity = layer.opacity / 100
        sprite.z = z
        sprite.tiles_x = int(gridx)
        sprite.tiles_y = int(gridy)
        return sprite

    def mkdir(self):
        ''' Make a destination dir for the sprites and json file '''
        try:
            if not os.path.isdir(self.sprite_path):
                os.makedirs(self.sprite_path)
            if not os.path.isdir(self.vector_path):
                os.makedirs(self.vector_path)
        except Exception, err:
            show_error_msg(err)

    def save_png(self, img, path):
        ''' Save img to path as png '''
        drw = pdb.gimp_image_active_drawable(img)
        pdb.file_png_save2(img,
                           drw,
                           path,
                           os.path.basename(path),
                           False,
                           9,
                           False,
                           False,
                           False,
                           False,
                           False,
                           1,
                           True)

    def write_json(self):
        ''' Write out the json config for the character '''
        sprites = []
        for sprite in self.sprites:
            sprites.append(sprite.get_data())
        data = { "name": self.name, "nodes": sprites }
        json_data = json.dumps(data,
                   sort_keys=True,
                   indent=4, separators=(',', ': '))
        sprite_file = open(self.json, "w")
        sprite_file.write(json_data)
        sprite_file.close()

    def crop_alpha_from_layer(self, img, layer, clear_selection=True):
        pdb.gimp_selection_layer_alpha(layer)
        pdb.gimp_selection_grow(img, 10)
        pdb.gimp_selection_feather(img, 50)

        x0,y0 = pdb.gimp_drawable_offsets(layer)
        non_empty, x1, y1, x2, y2 = pdb.gimp_selection_bounds(img)
        pdb.gimp_layer_resize(layer, x2-x1, y2-y1, x0-x1, y0-y1)
        if clear_selection:
            pdb.gimp_selection_clear(img)

    def selection_to_path(self, img, layer):
        names = [vector.name for vector in img.vectors]
        pdb.plug_in_sel2path(img, layer)
        updated_names = [vector.name for vector in img.vectors]
        vector_name = list(set(updated_names) - set(names))[0]

        for vector in img.vectors:
            if vector.name == vector_name:
                vector.name = layer.name


def show_error_msg( msg ):
    # Output error messages to the GIMP error console.
    origMsgHandler = pdb.gimp_message_get_handler()
    pdb.gimp_message_set_handler(ERROR_CONSOLE)
    pdb.gimp_message(msg)
    pdb.gimp_message_set_handler(origMsgHandler)

def export_to_coatools(img, drw, path, name):
    if name:
        export = CoaExport(img, path, name)
    else:
        show_error_msg("Please enter a file name.")


register(
    "python_fu_coatools",
    ("Tool for exporting layered characters and objects to\n"
     "Cutout Animation Tools: 2D Animation Tools for Blender\n\n"
     "See https://github.com/ndee85/coa_tools"),
    "GNU GPL v3 or later.",
    "Ragnar Brynjúlfsson",
    "Ragnar Brynjúlfsson",
    "April 2016",
    "Export to CoaTools...",
    "RGB*, GRAY*, INDEXED*",
    [
        (PF_IMAGE, "img", "Image", None),
        (PF_DRAWABLE, "drw", "Drawable", None),
        (PF_DIRNAME, "path", "Export to:", os.getcwd()),
        (PF_STRING, "name", "Name:", 'enter_name'),
    ],
    [],
    export_to_coatools,
    menu=("<Image>/File/Export"),
    domain=("gimp20-python", gimp.locale_directory)
)


main()
