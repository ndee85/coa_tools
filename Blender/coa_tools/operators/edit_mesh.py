'''
Copyright (C) 2015 Andreas Esau
andreasesau @ gmail.com

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

import os
import bpy
import bpy_extras
import bpy_extras.view3d_utils
import mathutils
from mathutils import Vector, Matrix, Quaternion, geometry
import math
import bmesh
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
from .. import functions
from .. functions_draw import  * 
# import bgl
# import blf
import gpu
from math import radians, degrees
import traceback
import gpu
from gpu_extras.batch import batch_for_shader
from .. import constants as CONSTANTS
import pdb


######################################################################################################################################### Grid Fill
def collapse_short_edges(bm,obj,threshold=1.0):
    ### collapse short edges
    edges_len_average = 0
    edges_count = 0
    shortest_edge = 10000
    for edge in bm.edges:
        if True:
            edges_count += 1
            length = edge.calc_length()
            edges_len_average += length
            if length < shortest_edge:
                shortest_edge = length
    edges_len_average = edges_len_average/edges_count

    verts = []
    for vert in bm.verts:
        if not vert.is_boundary:
            verts.append(vert)
    bmesh.update_edit_mesh(obj.data)
    
    bmesh.ops.remove_doubles(bm,verts=verts,dist=edges_len_average * threshold)

    bmesh.update_edit_mesh(obj.data)

def get_average_edge_length(bm,obj):
    edges_len_average = 0
    edges_count = 0
    shortest_edge = 10000
    for edge in bm.edges:
        if True:#edge.is_boundary:
            edges_count += 1
            length = edge.calc_length()
            edges_len_average += length
            if length < shortest_edge:
                shortest_edge = length
    edges_len_average = edges_len_average/edges_count
    return edges_len_average, shortest_edge

def clean_boundary_edges(bm,obj):
    edges_len_average, shortest_edge = get_average_edge_length(bm,obj)
    edges = []
    
    for edge in bm.edges:
        if edge.calc_length() < edges_len_average * .12 and not edge.tag:
            edges.append(edge)
    bmesh.ops.collapse(bm,edges=edges,uvs=False)        
    bmesh.update_edit_mesh(obj.data)        

def average_edge_cuts(bm,obj,cuts=1):
    ### collapse short edges
    edges_len_average, shortest_edge = get_average_edge_length(bm,obj)
    
    subdivide_edges = []
    for edge in bm.edges:
        cut_count = int(edge.calc_length()/shortest_edge) * cuts
        if cut_count < 0:
            cut_count = 0
        if not edge.is_boundary:
            subdivide_edges.append([edge,cut_count])
    for edge in subdivide_edges:
        bmesh.ops.subdivide_edges(bm,edges=[edge[0]],cuts=edge[1])
        bmesh.update_edit_mesh(obj.data)
                
def triangle_fill(bm,obj):
    edges = []
    for edge in bm.edges:
        if edge.select == True:
            edges.append(edge)
    triangle_fill = bmesh.ops.triangle_fill(bm,edges=edges,use_beauty=True)
    bmesh.update_edit_mesh(obj.data)
    if triangle_fill["geom"] == []:
        return False
    else:
        return True

def triangulate(bm,obj):
    bmesh.ops.triangulate(bm,faces=bm.faces) 
    bmesh.update_edit_mesh(obj.data)
    
def smooth_verts(bm,obj):
    ### smooth verts
    smooth_verts = []
    for vert in bm.verts:
        if not vert.is_boundary:
            smooth_verts.append(vert)
    for i in range(50):
        #bmesh.ops.smooth_vert(bm,verts=smooth_verts,factor=1.0,use_axis_x=True,use_axis_y=True,use_axis_z=True)    
        bmesh.ops.smooth_vert(bm,verts=smooth_verts,factor=1.0,use_axis_x=True,use_axis_y=True,use_axis_z=True)    
    bmesh.update_edit_mesh(obj.data)
    
def clean_verts(bm,obj):
    ### find corrupted faces
    faces = []     
    for face in bm.faces:
        i = 0
        for edge in face.edges:
            if not edge.is_manifold:
                i += 1
            if i == len(face.edges):
                faces.append(face)           
    bmesh.ops.delete(bm,geom=faces,context="FACES_ONLY")

    edges = []
    for face in bm.faces:
        i = 0
        for vert in face.verts:
            if not vert.is_manifold and not vert.is_boundary:
                i+=1
            if i == len(face.verts):
                for edge in face.edges:
                    if edge not in edges:
                        edges.append(edge)
    bmesh.ops.collapse(bm,edges=edges)
    
    bmesh.update_edit_mesh(obj.data)
    for vert in bm.verts:
        if not vert.is_boundary:
            vert.select = False
            
    verts = []
    for vert in bm.verts:
        if len(vert.link_edges) in [3,4] and not vert.is_boundary:
            verts.append(vert)
    bmesh.ops.dissolve_verts(bm,verts=verts)
    bmesh.update_edit_mesh(obj.data)

def remove_doubles(obj,edge_average_len,edge_min_len):
    bm = bmesh.from_edit_mesh(obj.data)
    verts = []
    for vert in bm.verts:
        if not vert.hide:
            verts.append(vert)
    bmesh.ops.remove_doubles(bm,verts=verts,dist=0.0001)
    bmesh.update_edit_mesh(obj.data)     
        

class COATOOLS_OT_ReprojectSpriteTexture(bpy.types.Operator):
    bl_idname = "coa_tools.reproject_sprite_texture"
    bl_label = "Reproject Sprite Texture"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    def reproject(self,context):
        ### unwrap
        obj = context.active_object
        hide_base_sprite = obj.data.coa_tools.hide_base_sprite
        obj.data.coa_tools.hide_base_sprite = False
        bpy.ops.object.mode_set(mode="EDIT",toggle=False)
        bm = bmesh.from_edit_mesh(obj.data)
        
        selected_verts = []
        for vert in bm.verts:
            if vert.select:
                selected_verts.append(vert.co)
                #vert.select = True
        
        for face in bm.faces:
            face.select = True
        for vert in bm.verts:
            vert.select = True

        object_matrix = obj.matrix_world.copy()
        obj.rotation_euler = [0,0,0]
        obj.scale = [1,1,1]
        bpy.ops.uv.project_from_view(camera_bounds=False, correct_aspect=True, scale_to_bounds=True)        
        obj.matrix_world = object_matrix
        for face in bm.faces:
            face.select = False
        bmesh.update_edit_mesh(obj.data)    
        
        for vert in bm.verts:
            if vert.co in selected_verts:
                vert.select = True
            else:
                vert.select = False
                
        bmesh.update_edit_mesh(obj.data)    
        obj.data.coa_tools.hide_base_sprite = hide_base_sprite
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        self.reproject(context)
        return {"FINISHED"}
        

class COATOOLS_OT_GenerateMeshFromEdgesAndVerts(bpy.types.Operator):
    bl_idname = "coa_tools.generate_mesh_from_edges_and_verts"
    bl_label = "Generate Mesh From Edges And Verts"
    bl_description = ""
    bl_options = {"REGISTER"}     

    def cleanup_and_fill_mesh(self,obj,bm):
        context = bpy.context
        wm = context.window_manager
        wm.progress_begin(0,100)
        
        def edge_is_intersecting(e2,bm):
            for e1 in bm.edges:
                edge_visible = not e1.hide
                edge_not_same = e1.verts[0] not in e2 and e1.verts[1] not in e2
                if edge_visible and edge_not_same:
                    i = geometry.intersect_line_line_2d(e1.verts[0].co.xz, e1.verts[1].co.xz, e2[0].co.xz, e2[1].co.xz)
                    if i != None:
                        return True
            return False   
        
        def get_linked_verts(vert):
            linked_verts = [vert]
            outer_verts = [vert]
            while len(outer_verts) > 0:
                new_verts = []
                for outer_vert in outer_verts:
                    for edge in outer_vert.link_edges:
                        other_vert = edge.other_vert(outer_vert)
                        if other_vert not in linked_verts:
                            linked_verts.append(other_vert)
                            new_verts.append(other_vert)
                outer_verts = new_verts
            return linked_verts

        ### delete faces
        faces = []
        for face in bm.faces:
            if not face.hide:
                face_editable = True
                for vert in face.verts:
                    if vert.hide:
                        face_editable = False
                        break
                if face_editable:    
                    faces.append(face)
                
        bmesh.ops.delete(bm,geom=faces,context="FACES_ONLY")
        wm.progress_update(30)
        ### delete double verts
        edges_len_average, shortest_edge = get_average_edge_length(bm, context.active_object)
        verts = []
        for edge in bm.edges:
            if not edge.hide:
                if edge.calc_length() < edges_len_average * .01:
                    if edge.verts[0] not in verts:
                        verts.append(edge.verts[0])
                    if edge.verts[1] not in verts:
                        verts.append(edge.verts[1])
        bmesh.ops.remove_doubles(bm,verts=verts,dist=0.01)            
        
        ### delete intersecting lines and add vertices at intersectionpoints
        intersection_points = []
        to_be_deleted = []
        for e1 in bm.edges:
            for e2 in bm.edges:
                edges_not_visible = not e1.hide and not e2.hide
                
                edges_share_points = e1.verts[0].co.xz in [e2.verts[0].co.xz, e2.verts[1].co.xz] or e1.verts[1].co.xz in [e2.verts[0].co.xz, e2.verts[1].co.xz]
                
                if e1 != e2 and not edges_share_points and edges_not_visible:
                    i = geometry.intersect_line_line_2d(e1.verts[0].co.xz, e1.verts[1].co.xz, e2.verts[0].co.xz, e2.verts[1].co.xz)
                    
                    if i != None:
                        i_3d = Vector((i[0],e1.verts[0].co[1],i[1]))
                        if e1 not in to_be_deleted:
                            to_be_deleted.append(e1)
                        if e2 not in to_be_deleted:
                            to_be_deleted.append(e2)
                        if i_3d not in intersection_points:
                            intersection_points.append(i_3d)
        for edge in to_be_deleted:
            bm.edges.remove(edge)
        for p in intersection_points:
            bm.verts.new(p)
    
        def get_vertex_loops(bm):
            ### find single vertex loops
            all_verts = []
            vert_loops = []
            for vert in bm.verts:
                if not vert.hide:
                    if vert not in all_verts:
                        loop_list = get_linked_verts(vert)
                        vert_loops.append(loop_list)
                        all_verts += loop_list
            return vert_loops            
        ### connect loose verts
        connected_edges = []
        for vert in bm.verts:
            if not vert.hide and len(vert.link_edges) == 0:
                distance = 1000000000000000
                vert_a = None
                vert_b = None
                for vert2 in bm.verts:
                    edge_center = (vert.co+vert2.co) * .5
                    if vert != vert2 and vert2.co != vert.co:# and edge_center not in connected_edges:
                        if (vert.co - vert2.co).magnitude < distance:
                            distance = (vert.co - vert2.co).magnitude
                            vert_a = vert
                            vert_b = vert2
                if vert_a != None and vert_b != None:
                    edge_center = (vert_a.co+vert_b.co) * .5
                    if edge_center not in connected_edges:
                        bm.edges.new([vert_a,vert_b])
                        connected_edges.append(edge_center) 
                        
        ### connect loose edges
        vert_loops = get_vertex_loops(bm)
        connected_edges = []
        if len(vert_loops) > 0:
            for i,loop in enumerate(vert_loops):
                for vert in loop:
                    exclude_verts = [vert.link_edges[0].other_vert(vert), vert] if len(vert.link_edges) > 0 else [vert]
                    distance = 1000000000000000
                    vert_a = None
                    vert_b = None
                    if len(vert.link_edges) == 1:
                        for j,loop_next in enumerate(vert_loops):
                            for vert2 in loop_next:
                                if vert2 != vert:
                                    edge1 = (vert.co - vert.link_edges[0].other_vert(vert).co).normalized()
                                    edge2 = (vert.co - vert2.co).normalized()
                                    if edge1.length > 0 and edge2.length > 0:
                                        angle = degrees(edge1.angle(edge2))
                                        
                                        if (vert.co - vert2.co).magnitude < distance and vert2 not in exclude_verts and abs(angle) > 30 and not edge_is_intersecting([vert,vert2],bm):
                                            
                                            distance = (vert.co - vert2.co).magnitude
                                            vert_a = vert
                                            vert_b = vert2
                                
                    ### connect nearest points and check 
                    ### if they haven't been connected yet by finding the edge center
                    if vert_a != None and vert_b != None:
                        edge_center = (vert_a.co+vert_b.co) * .5
                        if edge_center not in connected_edges:
                            bm.edges.new([vert_a,vert_b])
                            connected_edges.append(edge_center)                    
                            
        wm.progress_update(100)
        ### find nearest vertex of different loops and connect
        vert_loops = get_vertex_loops(bm)
        connected_edges = []
        if len(vert_loops) > 1:
            ### loop over all edge loops and find nearest vertex points of two loops to connect
            for i,loop in enumerate(vert_loops):
                
                distance = 1000000000000000
                vert_a = None
                vert_b = None
                
                for j,loop_next in enumerate(vert_loops):
                    if j != i:
                        for vert in loop:
                            for vert2 in loop_next:
                                if (vert.co - vert2.co).magnitude < distance:
                                    distance = (vert.co - vert2.co).magnitude
                                    vert_a = vert
                                    vert_b = vert2
                        
                ### connect nearest points and check 
                ### if they haven't been connected yet by finding the edge center
                if vert_a != None and vert_b != None:
                    edge_center = (vert_a.co+vert_b.co) * .5
                    if edge_center not in connected_edges:
                        bm.edges.new([vert_a,vert_b])
                        connected_edges.append(edge_center)             


        ### store existing edges center
        edges_center = []
        for edge in bm.edges:
            edges_center.append((edge.verts[0].co + edge.verts[1].co) * .5)

        ### fill edges
        edges = []
        for edge in bm.edges:
            if not edge.hide:
                edges.append(edge)
        bmesh.ops.triangle_fill(bm,use_beauty=True,use_dissolve=True,edges=edges)

        ### delete newly created edges after using the triangle fill operator
        delete_edges = []
        for edge in bm.edges:
            if not edge.hide and not edge.verts[0].hide and not edge.verts[1].hide:
                edge_center = (edge.verts[0].co + edge.verts[1].co) * .5
                if edge_center not in edges_center and edge.is_boundary:
                    delete_edges.append(edge)
        bmesh.ops.delete(bm, geom=delete_edges, context="EDGES")

        delete_edges = []       
        for edge in bm.edges:
            if not edge.hide and edge.is_wire and not edge.verts[0].hide and not edge.verts[1].hide:
                delete_edges.append(edge)
        bmesh.ops.delete(bm, geom=delete_edges, context="EDGES")


        ### triangulate mesh
        faces = []
        for face in bm.faces:
            if not face.hide:
                face_editable = True
                for vert in face.verts:
                    if vert.hide:
                        face_editable = False
                        break
                if face_editable:    
                    faces.append(face)
        bmesh.ops.triangulate(bm,faces=faces)   
                    
        ### update mesh            
        bmesh.update_edit_mesh(obj.data)
        wm.progress_end()
        
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        
        obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        self.cleanup_and_fill_mesh(obj,bm)
        bpy.ops.coa_tools.reproject_sprite_texture()
        
        return {"FINISHED"}

######################################################################################################################################### Draw Contours
''' scene.ray_cast return values for Blender 2.77
Return (hit, hit_location,hit_normal,?,hit_object,matrix)
'''

''' scene.ray_cast return values for Blender 2.76
Return (hit, hit_object,matrix,hit_location,hit_normal)

result = bpy.context.scene.ray_cast(start,end)
result = [result[0],result[4],result[5],result[1],result[2]]
'''

class COATOOLS_TO_DrawPolygon(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'

    # The prefix of the idname should be your add-on name.
    bl_idname = "coa_tools.draw_polygon"
    bl_label = "Draw 2D Polygon"
    bl_description = (
        "Draws COA Tools Mesh Polygon"
    )
    bl_icon = os.path.join(functions.get_coa_tools_dir(), "icons", "coa_tools.draw_polygon")
    bl_widget = None
    # bl_keymap = (
    #     ("coa_tools.draw_polygon", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
    # )


class COATOOLS_OT_DrawContour(bpy.types.Operator):
    bl_idname = "coa_tools.edit_mesh"
    bl_label = "Edit Mesh"
    
    mode: StringProperty(default="EDIT_MESH")
    new_shape_name: StringProperty()
    
    def __init__(self):
        self.type = ""
        self.value = ""
        self.ctrl = False
        self.alt = False
        self.shift = False
        self.distance = .1
        self.cur_distance = 0
        self.draw_dir = Vector((0,0,0))
        self.old_coord = Vector((0,0,0))
        self.mouse_press = False
        self.mouse_press_hist = False
        self.mouse_pos_3d = Vector((0,0,0))
        self.mouse_2d_x = 0
        self.mouse_2d_y = 0
        self.inside_area = False
        self.cursor_pos_hist = Vector((1000000000,0,1000000))
        self.sprite_object = None
        self.in_view_3d = False
        self.nearest_vertex_co = Vector((0,0,0))
        self.contour_length = 0
        
        self.selected_verts_count = 0
        self.selected_vert_coord = None
        self.visible_verts = []
        self.visible_edges = []
        self.intersection_points = []
        self.edge_slide_points = []
        self.new_added_edges = []
        self.cut_edge = False
        
        self.edit_object = None
        self.edit_object_name = ""
        self.texture_preview_object = None
        self.texture_preview_object_name = ""
        
        self.bone = None
        self.bone_shape = None
        self.draw_bounds = False
        self.display_type = ""
        self.draw_handler_removed = False
        self.bounds = []
        self.type_prev = ""
        self.value_prev = ""
        self.prev_coa_view = ""
        
        self.armature = None
        self.armature_pose_mode = ""
        
        self.snapped_vert_coord, self.point_type, self.bm_obj, self.verts_edges_data = [Vector((0,0,0)),None,None,None]
        
        self.click_drag = False
        self.first_added_vert = None
        self.delete_stroke_points = []
    
    def project_cursor(self, event):
        coord = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
        transform = bpy_extras.view3d_utils.region_2d_to_location_3d
        region = bpy.context.region
        rv3d = bpy.context.space_data.region_3d
        #### cursor used for the depth location of the mouse
        #depth_location = bpy.context.scene.cursor_location
        depth_location = bpy.context.active_object.location
        ### creating 3d vector from the cursor
        end = transform(region, rv3d, coord, depth_location)
        #end = transform(region, rv3d, coord, bpy.context.space_data.region_3d.view_location)
        ### Viewport origin
        start = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        ### Cast ray from view to mouselocation
        if functions.b_version_smaller_than((2,91,0)):
            ray = bpy.context.scene.ray_cast(bpy.context.view_layer, start, (start+(end-start) * 2000)-start )
        else:
            ray = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, start, (start + (end - start) * 2000) - start)
        ray = [ray[0], ray[4], ray[5], ray[1], ray[2]]
        return start, end, ray

    def set_paint_distance(self,context,ray):
        ob = context.active_object
        scene = context.scene
        
        bpy.ops.object.mode_set(mode='OBJECT')
        if len(ob.data.vertices)==0:
            bpy.ops.object.mode_set(mode='EDIT')
            return 0.0
        
        vert_loc = ob.data.vertices[len(ob.data.vertices)-1].co
        distance = (ray - vert_loc - ob.location).magnitude
        bpy.ops.object.mode_set(mode='EDIT')
        return distance
    
    def limit_value(self,value,minn,maxn):
        return max(min(maxn,value),minn)
    
    def limit_cursor_by_bounds(self,context,location):
        if self.mode == "EDIT_MESH":
            obj = context.active_object
            bounds = []
            for point in self.bounds:
                bounds.append(obj.matrix_world.inverted() @ point)
            location = obj.matrix_world.inverted() @ location
            
            location[0] = self.limit_value(location[0], bounds[1][0], bounds[2][0])
            location[2] = self.limit_value(location[2], bounds[0][2], bounds[1][2])
            location = obj.matrix_world @ location
        return location
    
    
    def clean_mesh(self,obj):
        bm = bmesh.from_edit_mesh(obj.data)
        
        faces = []
        for face in bm.faces:
            if not face.hide:
                face_ok = False
                invalid_edges = 0
                for edge in face.edges:
                    if not edge.is_manifold and not edge.is_wire and not edge.is_boundary:
                        invalid_edges += 1
                        
                if invalid_edges == len(face.edges):
                    faces.append(face)
        bmesh.ops.delete(bm,geom=faces,context="FACES_ONLY")
        bmesh.update_edit_mesh(obj.data)
        
    def draw_verts(self,context,obj,bm,position,use_snap=False):
        scene = context.scene
        obj_matrix = obj.matrix_world
        if scene.coa_tools.surface_snap:
            snapped_pos, type, bm_ob = self.snapped_vert_coord , self.point_type , self.bm_objs
        else:
            snapped_pos, type, bm_ob = [self.mouse_pos_3d,None,None]
        if not use_snap:
            snapped_pos = position
        
        snapped_pos = self.limit_cursor_by_bounds(context,snapped_pos)
        
        for edge in bm.edges:
            edge.select = False
        for vert in bm.verts:
            vert.select = False
        for face in bm.faces:
            face.select = False     
        
        intersect_prev_vert = bm.select_history[0] if len(bm.select_history) > 0 else None
        for i,p in enumerate(self.intersection_points):
            for edge in bm.edges:
                sub_edge = None
                c = self.get_projected_point(edge,custom_pos=p,disable_edge_threshold=True)
                if (c - p).magnitude < 0.001:
                    sub_edge = edge
                    break
            if sub_edge != None:
                divider = (obj.matrix_world @ sub_edge.verts[0].co - obj.matrix_world @ sub_edge.verts[1].co).magnitude
                if divider != 0:
                    percentage = (obj.matrix_world @ sub_edge.verts[0].co - c).magnitude / (obj.matrix_world @ sub_edge.verts[0].co - obj.matrix_world @ sub_edge.verts[1].co).magnitude
                    new_edge,new_vert = bmesh.utils.edge_split(sub_edge,sub_edge.verts[0],percentage)
                    
                    bm.select_history = [new_vert]
                    try:
                        edge = bm.edges.new([intersect_prev_vert,new_vert])
                        self.new_added_edges.append(edge)
                    except:
                        print("Edge already exists.")
                    intersect_prev_vert = new_vert
        
        if type == "VERT" and use_snap:
            if self.contour_length > 0 and len(bm.select_history) > 0:
                new_vert = bm_ob
                try:
                    edge = bm.edges.new([bm.select_history[0],new_vert])
                    self.new_added_edges.append(edge)
                except:    
                    print("Edge already exists.")
                bm.select_history = [new_vert]
                self.selected_vert_coord = obj_matrix @ new_vert.co
                new_vert.select = True
            else:
                new_vert = bm_ob
                bm.select_history = [new_vert]
                self.selected_vert_coord = obj_matrix @ new_vert.co
                new_vert.select = True
                
            
            if self.contour_length == 0:    
                self.contour_length += 1
                
        elif type == "EDGE" and use_snap:
            sub_edge = bm_ob
            if sub_edge != None:
                c = self.get_projected_point(sub_edge)
                divider = (obj.matrix_world @ sub_edge.verts[0].co - obj.matrix_world @ sub_edge.verts[1].co).magnitude
                if divider != 0:
                    percentage = (obj.matrix_world @ sub_edge.verts[0].co - c).magnitude / (obj.matrix_world @ sub_edge.verts[0].co - obj.matrix_world @ sub_edge.verts[1].co).magnitude
                    new_edge,new_vert = bmesh.utils.edge_split(sub_edge,sub_edge.verts[0],percentage)
                    if sub_edge in self.new_added_edges:
                        self.new_added_edges.append(new_edge)
                    bm.select_history = [new_vert]
                    new_vert.select = True
                    self.selected_vert_coord = obj_matrix @ new_vert.co
                    try:
                        pass
                        if self.contour_length > 0:
                            edge = bm.edges.new([intersect_prev_vert,new_vert])
                            self.new_added_edges.append(edge)
                            #edge.select = True
                    except:
                        print("Edge already exists.")
                
                if self.contour_length == 0:    
                    self.contour_length += 1
                    self.selected_vert_coord = obj_matrix @ new_vert.co
                    
        else:
            new_vert = bm.verts.new(obj_matrix.inverted() @ snapped_pos)
                
            bmesh.update_edit_mesh(obj.data)
            
            if self.contour_length > 0 and len(bm.select_history) > 0:
                edge = bm.edges.new([bm.select_history[0],new_vert])
                self.new_added_edges.append(edge)
                
            self.selected_vert_coord = obj_matrix @ new_vert.co
            new_vert.select = True
            bm.select_history = [new_vert]
            
            self.contour_length += 1
            
        bmesh.update_edit_mesh(obj.data)
    
    def set_bone_shape_color_and_wireframe(self,context,obj):
        bm = bmesh.from_edit_mesh(obj.data)
        if len(bm.faces) > 0:
            self.armature.data.bones[self.bone.name].show_wire = False
        else:
            self.armature.data.bones[self.bone.name].show_wire = True
        bm.free()    
    
    def check_verts(self,context,event):
        verts = []
        bm = bmesh.from_edit_mesh(context.active_object.data)
        for vert in bm.verts:
            if vert.select:
                verts.append(vert)
        for vert in verts:
            vert.co = context.active_object.matrix_world.inverted() @ self.limit_cursor_by_bounds(context,context.active_object.matrix_world @ vert.co)
        bmesh.update_edit_mesh(context.active_object.data)
    
    
    def get_selected_vert_pos(self,context):
        bm = bmesh.from_edit_mesh(context.active_object.data)
        for vert in bm.verts:
            if vert.select == True:
                bmesh.update_edit_mesh(context.active_object.data)
                return vert.co
        bmesh.update_edit_mesh(context.active_object.data)
        return None
        
    def check_selected_verts(self,context):
        bm = bmesh.from_edit_mesh(context.active_object.data)
        return bm.select_history
    
    
    def get_projected_point(self,edge,custom_pos=None,disable_edge_threshold=False):
        context = bpy.context
        obj = context.active_object
        mouse_pos = custom_pos if custom_pos != None else self.mouse_pos_3d
        if type(edge) == bmesh.types.BMEdge:
            v1 = obj.matrix_world @ edge.verts[0].co
            v2 = obj.matrix_world @ edge.verts[1].co
        elif type(edge) == list:
            v1 = obj.matrix_world @ edge[0]
            v2 = obj.matrix_world @ edge[1]
        
        dist = min((v1-v2).magnitude * .5 , context.scene.coa_tools.snap_distance * context.space_data.region_3d.view_distance)
        if disable_edge_threshold:
            dist = 0
        
        p1 = (v1 - v2).normalized()
        p2 = mouse_pos - v2
        l = max(min(p2.dot(p1), (v1 - v2).magnitude - dist),0 + dist)
        c = (v2 + l * p1)
        return c
    
    def get_edge_slide_points(self,context,bm):
        obj = context.active_object
        
        snap_distance = context.scene.coa_tools.snap_distance * context.space_data.region_3d.view_distance
        
        edge_slide_points = []
        for edge in bm.edges:
            bm.edges.ensure_lookup_table()
            if not edge.hide:
                vert_1 = obj.matrix_world @ edge.verts[0].co
                vert_2 = obj.matrix_world @ edge.verts[1].co
                
                left = min(vert_1.x , vert_2.x) - snap_distance
                right = max(vert_1.x , vert_2.x) + snap_distance
                top = max(vert_1.z , vert_2.z) + snap_distance
                bottom = min(vert_1.z , vert_2.z) - snap_distance
                
                if self.mouse_pos_3d.x > left and self.mouse_pos_3d.x < right and self.mouse_pos_3d.z < top and self.mouse_pos_3d.z > bottom: 
                    c = self.get_projected_point(edge)
                    edge_slide_points.append([c,edge])
                
        return edge_slide_points
    
    def get_visible_verts(self,context,bm):
        obj = context.active_object
        visible_verts = []
        self.selected_verts_count = 0
        
        
        active_vert = None
        if len(bm.select_history)>0 and type(bm.select_history[0]) == bmesh.types.BMVert:
            active_vert = bm.select_history[0]
        for vert in bm.verts:
            if not vert.hide and vert.select:
                self.selected_verts_count += 1
            if not vert.hide:
                visible_verts.append([obj.matrix_world @ vert.co , vert])
        return visible_verts
    
    def snap_to_edge_or_vert(self,coord, get_bm_obj = False):
        obj = bpy.context.active_object
        context = bpy.context
        scene = bpy.context.scene
        distance = scene.coa_tools.snap_distance * bpy.context.space_data.region_3d.view_distance
        snap_coord = coord
        point_type = None
        bm_obj2 = None
        verts_edges_data = None
        
        points = []
        for e,edge in self.edge_slide_points:
            points.append([e,"EDGE",edge])
            
        for p,vert in self.visible_verts:
            points.append([p,"VERT",vert])
        
        for vert,type,bm_obj in points:
            
            if (vert - coord).magnitude < distance:
                if type == "VERT":
                    distance = (vert - coord).magnitude
                snap_coord = vert
                point_type = type
                
                bm_obj2 = bm_obj
                if "Vert" in str(bm_obj):
                    verts_edges_data = [bm_obj.co]
                elif "Edge" in str(bm_obj):
                    verts_edges_data = [bm_obj.verts[0].co,bm_obj.verts[1].co]
        return [snap_coord , point_type , bm_obj2 , verts_edges_data]
        
    def get_intersecting_lines(self,coord,bm):
        scene = bpy.context.scene
        
        if scene.coa_tools.surface_snap:
            coord, point_type, bm_ob = self.snapped_vert_coord , self.point_type , self.bm_objs
        else:    
            coord, point_type, bm_ob = [None,None,None]
            
        coord = self.limit_cursor_by_bounds(bpy.context,coord)
        
        intersection_points = []
        if self.selected_vert_coord != None and coord != None:
            obj = bpy.context.active_object
            e1 = [self.selected_vert_coord.xz,coord.xz]
            for edge in bm.edges:
                if not edge.hide:# and (edge.is_wire or edge.is_boundary):
                    e2 = [(obj.matrix_world @ edge.verts[0].co).xz , (obj.matrix_world @ edge.verts[1].co).xz ]
                    ip = geometry.intersect_line_line_2d(e1[0],e1[1],e2[0],e2[1])
                    if ip != None:
                        ip = Vector((ip[0],self.selected_vert_coord[1],ip[1]))
                        if (ip - self.selected_vert_coord).magnitude > 0.001 and (ip - coord).magnitude > 0.001:
                            intersection_points.append(ip)
        intersection_points.sort(key=lambda x: (self.selected_vert_coord - x).magnitude)
        return intersection_points         
    
    def delete_geometry(self,context,bm,position,single_vert=False):
        obj = context.active_object
        snapped_vert_coord , point_type , bm_ob = self.snapped_vert_coord , self.point_type , self.bm_objs
        if point_type == "VERT":
            vert = bm_ob
            
            delete_verts = [vert]
            for edge in vert.link_edges:
                other_vert = edge.other_vert(vert)
                if len(other_vert.link_edges) == 1:
                    delete_verts.append(other_vert)
            for vert in delete_verts:
                bm.verts.remove(vert)
                    
        elif point_type == "EDGE":
            edge = bm_ob
            
            verts = []
            for vert in edge.verts:
                verts.append(vert)
                
                
            delete_edges = [edge]
            for edge in delete_edges:
                bm.edges.remove(edge)    
            
            for vert in verts:
                if len(vert.link_edges) == 0:
                    bm.verts.remove(vert)
            
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
            
        bmesh.update_edit_mesh(obj.data)                  

    def suspend_area_fullscreen(self, context, event):
        if self.ctrl and event.type == "SPACE":
            return 'SUSPEND'
        return 'PASS_THROUGH'

    def modal(self, context, event):
        if context.active_object.active_shape_key_index != 0:
            context.active_object.active_shape_key_index = 0
        if self.suspend_area_fullscreen(context, event) == "SUSPEND":
            return {'RUNNING_MODAL'}

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        try:
            wm = context.window_manager
            ### set variables
            self.mouse_2d_x = event.mouse_region_x
            self.mouse_2d_y = event.mouse_region_y
            obj = context.active_object
            self.type = str(event.type)
            self.value = str(event.value)
            self.ctrl = bool(event.ctrl)
            self.alt = bool(event.alt)
            self.shift = bool(event.shift)
            self.in_view_3d = functions.check_region(context, event)
            scene = context.scene
            
            ### map mouse button
            click_button = None
            select_button = None
            keyconfig = wm.keyconfigs.active
            click_button = 'LEFTMOUSE'
            select_button = 'RIGHTMOUSE'
            
            
            ### leave edit mode
            if context.active_object == None or (context.active_object != None and context.active_object.type == "MESH" and context.active_object.mode != "EDIT" and not self.draw_handler_removed) or self.sprite_object.coa_tools.edit_mesh == False or context.active_object.type != "MESH":
                return self.exit_edit_mode(context,event)
            self.obj = bpy.context.active_object
            ### create bmesh object
            bm = bmesh.from_edit_mesh(obj.data)

            ### limit verts within bounds -> resets vertex positions to stay within bounds
            if self.type_prev in ["G","S","R"] or (self.value_prev in["CLICK","PRESS"] and self.value == "RELEASE"):
                self.check_verts(context,event)

            ## skip everything if different tool is selected
            if functions.get_active_tool("EDIT_MESH") != "coa_tools.draw_polygon":
                return {'PASS_THROUGH'}
            
            if self.in_view_3d and context.active_object != None and self.type not in ["MIDDLEMOUSE"] and self.sprite_object.coa_tools.edit_mesh and click_button not in [select_button]:
                ### set click drag    
                if self.type == click_button:
                    self.click_drag = True
                if self.click_drag and self.value == "RELEASE":
                    self.click_drag = False
                    if event.ctrl:
                        bpy.ops.ed.undo_push(message="Delete Contour")
                    else:
                        bpy.ops.ed.undo_push(message="Draw Contour")
                ### set mouse press history
                self.mouse_press_hist = self.mouse_press
                
                ### Cast Ray from mousePosition and set Cursor to hitPoint
                rayStart,rayEnd, ray = self.project_cursor(event)
                
                
                if rayEnd != None:
                    pos = rayEnd
                    pos[1] = obj.matrix_world.to_translation()[1]-0.00001
                    self.mouse_pos_3d = rayEnd

                ### get visible verts in list | get intersecting points | get edge slide points  -> add everything in separate lists
                self.visible_verts = self.get_visible_verts(context,bm)
                if scene.coa_tools.surface_snap:
                    self.edge_slide_points = self.get_edge_slide_points(context,bm)
                    
                    self.snapped_vert_coord, self.point_type, self.bm_objs, self.verts_edges_data = self.snap_to_edge_or_vert(self.mouse_pos_3d)
                else:
                    self.snapped_vert_coord, self.point_type, self.bm_objs, self.verts_edges_data = [self.mouse_pos_3d,None,None,None]
                
                if self.contour_length > 0 and not self.alt:
                    self.intersection_points = self.get_intersecting_lines(self.mouse_pos_3d,bm)
                else:
                    self.intersection_points = []
                
                self.snapped_vert_coord = self.limit_cursor_by_bounds(context, self.snapped_vert_coord)
                
                    
                ### check if mouse is in 3d View
                coord = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
                view_3d_width = bpy.context.area.width - bpy.context.area.regions[5].width
                if coord[0] < 0 or coord[0] > view_3d_width:
                    self.inside_area = False
                    bpy.context.window.cursor_set("DEFAULT")
                elif coord[1] < 0 or coord[1] > bpy.context.area.height:
                    self.inside_area = False
                    bpy.context.window.cursor_set("DEFAULT")
                else:
                    self.inside_area = True
                    
                    if self.alt:
                        bpy.context.window.cursor_set("CROSSHAIR")
                    elif not self.alt and not self.shift:
                        if self.point_type == "EDGE":
                            bpy.context.window.cursor_set("KNIFE")
                        else:
                            bpy.context.window.cursor_set("PAINT_BRUSH")
                if not self.inside_area:
                    return {'PASS_THROUGH'}
                ### Set Mouse click
                if (event.value == 'PRESS' or event.value == 'CLICK') and event.type == click_button and self.mouse_press == False and not self.ctrl and not self.shift:
                    if not self.alt:
                        self.mouse_press = True
                        
                        ### add vert on first mouse press
                        self.cursor_pos_hist = Vector(self.mouse_pos_3d)

                        self.draw_verts(context,obj,bm,self.cursor_pos_hist,use_snap=True)
                    return{'RUNNING_MODAL'}
                    
                if (event.value == 'RELEASE' and (event.type == 'MOUSEMOVE' or event.type == 'LEFTMOUSE')):
                    self.mouse_press = False

                
                
                self.cur_distance = (self.mouse_pos_3d - self.cursor_pos_hist).magnitude
                self.draw_dir = (self.mouse_pos_3d - self.cursor_pos_hist).normalized()

                
                ### add verts while mouse is pressed and moved
                if not self.ctrl:
                    if self.mouse_press and self.inside_area:
                        if self.cur_distance > context.scene.coa_tools.distance:
                            i = int(self.cur_distance / (context.scene.coa_tools.distance))
                            for j in range(i):
                                new_vertex_pos = (self.cursor_pos_hist + (self.draw_dir * context.scene.coa_tools.distance))
                                self.draw_verts(context, obj, bm, new_vertex_pos, use_snap=False)

                                self.cursor_pos_hist = Vector(new_vertex_pos)
                    else:
                        self.old_coord = Vector((100000,100000,100000))

                ### check selected verts
                select_history = self.check_selected_verts(context)
                    
                    
                if self.type_prev in ["G"] and self.contour_length > 0:
                    if len(select_history) > 0 and type(select_history[0]) == bmesh.types.BMVert:
                        self.selected_vert_coord = obj.matrix_world @  select_history[0].co
                
                ### finishing edge drawing
                if self.contour_length == 0 and len(self.new_added_edges) > 0:                
                    self.new_added_edges = []
                
                scene.tool_settings.double_threshold = scene.coa_tools.snap_distance
                ### delete verts
                if self.alt and (self.click_drag or self.type == click_button) and not self.type in ["MIDDLEMOUSE"]:
                    self.selected_vert_coord = None
                    self.contour_length = 0
                    self.delete_geometry(context,bm,self.mouse_pos_3d)
                ### pick edge length
                if self.shift and self.point_type == "EDGE":
                    bpy.context.window.cursor_set("EYEDROPPER")
                    if self.type == click_button:
                        
                        p1 = obj.matrix_world @ self.verts_edges_data[0]
                        p2 = obj.matrix_world @ self.verts_edges_data[1]
                        length = (p1-p2).magnitude
                        scene.coa_tools.distance = length
                        
                        text = "Stroke Distance set to "+str(round(length,2))
                        self.report({"INFO"},text)
                
                ### remove last selected vert coord if nothing is selected
                if (self.selected_verts_count == 0 and self.selected_vert_coord != None) or self.type in [select_button] or (self.ctrl and self.type in ["Z"]):# or self.type_prev in ["G"]:
                    self.selected_vert_coord = None
                    self.contour_length = 0
                
                ### deselect verts
                if event.type in ["ESC","RET"]:
                    bm = bmesh.from_edit_mesh(context.active_object.data)
                    bm.select_history = []
                    for vert in bm.verts:
                        vert.select = False
                    for edge in bm.edges:
                        edge.select = False        
                    for face in bm.faces:
                        face.select = False    
                        
                
                if (event.type in {'TAB'} and not event.ctrl):
                    self.sprite_object.coa_tools.edit_mesh = False
                    bpy.ops.object.mode_set(mode='OBJECT')
            
            self.type_prev = str(event.type)
            self.value_prev = str(event.value)
        except Exception as e:
            traceback.print_exc()
            self.report({"ERROR"},"An Error occured, please check console for more Information.")
            self.exit_edit_mode(context,event,error=True)
        return {'PASS_THROUGH'}
    
    def exit_edit_mode(self,context,event,error=False):
        if not error:
            self.finish_edit_object(context)
        if self.draw_handler != None:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
            self.draw_handler = None
        # bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler2, "WINDOW")
        
        self.draw_handler_removed = True
        self.sprite_object = functions.get_sprite_object(context.active_object)
        self.sprite_object.coa_tools.edit_mesh = False
        self.sprite_object.coa_tools.edit_mode = "OBJECT"

        bpy.context.window.cursor_set("CROSSHAIR")
        if context.active_object != None:
            bpy.ops.object.mode_set(mode="OBJECT")
        self.sprite_object.coa_tools.edit_mesh = False
        functions.set_local_view(False)

        obj = context.active_object
        context.view_layer.objects.active = bpy.data.objects[self.edit_object_name] if self.edit_object_name in bpy.data.objects else None
        context.scene.coa_tools.view = self.prev_coa_view
        if context.active_object != None:
            bpy.ops.object.mode_set(mode="EDIT")
        if self.mode == "DRAW_BONE_SHAPE":
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
            bpy.ops.mesh.normals_make_consistent()
            bpy.ops.mesh.select_all(action='DESELECT')

            self.set_bone_shape_color_and_wireframe(context,self.bone_shape)

        bpy.context.window.cursor_set("CROSSHAIR")
        bpy.ops.object.mode_set(mode="OBJECT")

        self.sprite_object.coa_tools.edit_mesh = False
        functions.set_local_view(False)

        self.armature = functions.get_armature(self.sprite_object)
        if self.armature !=  None:
            self.armature.data.pose_position = self.armature_pose_mode

        if self.mode == "DRAW_BONE_SHAPE":
            self.armature.display_type = self.display_type
            context.scene.coa_tools.lock_to_bounds = self.draw_bounds
            if self.armature != None:
                context.view_layer.objects.active = self.armature
            if len(self.bone_shape.data.vertices) > 1:
                self.bone.custom_shape = self.bone_shape
                self.bone.use_custom_shape_bone_size = False
            else:
                self.bone.custom_shape = None

            self.bone_shape.select_set(False)
            self.bone_shape.parent = None
            context.collection.objects.unlink(self.bone_shape)
            context.view_layer.objects.active = self.armature
            self.armature.select_set(True)
            bpy.ops.object.mode_set(mode="POSE")
        else:
            if len(context.active_object.data.vertices) > 4:
                context.active_object.data.coa_tools.hide_base_sprite = True
            bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.objects.active = obj
        return{'FINISHED'}
    
    _timer = 0

    def prepare_edit_object(self, context):
        original_object = context.active_object

        keep_vert_index = []
        v_group = original_object.vertex_groups["coa_base_sprite"]
        for i,vert in enumerate(original_object.data.vertices):
            try:
                if v_group.weight(i) > 0:
                    keep_vert_index.append(i)
            except:
                pass

        if "COA TEXTURE PREVIEW" not in bpy.data.objects:
            texture_preview_object = original_object.copy()
            texture_preview_object.data = original_object.data.copy()
            texture_preview_object.name = "COA TEXTURE PREVIEW"
            context.collection.objects.link(texture_preview_object)
        else:
            texture_preview_object = bpy.data.objects["COA TEXTURE PREVIEW"]

        for mod in texture_preview_object.modifiers:
            if mod.name == "coa_base_sprite":
                texture_preview_object.modifiers.remove(mod)

        context.view_layer.objects.active = texture_preview_object
        bpy.ops.object.mode_set(mode="EDIT")
        if "coa_base_sprite" in texture_preview_object.vertex_groups:
            bm = bmesh.from_edit_mesh(texture_preview_object.data)
            for vert in bm.verts:
                vert.hide = False
                if vert.index not in keep_vert_index:
                    bm.verts.remove(vert)
        bpy.ops.object.mode_set(mode="OBJECT")

        context.view_layer.objects.active = original_object
        edit_object = context.active_object
        edit_object.select_set(True)
        edit_object.display_type = "WIRE"
        texture_preview_object.select_set(True)
        texture_preview_object.location[1] += .1

        return edit_object, texture_preview_object

    def finish_edit_object(self, context):
        functions.set_active_tool(self, context, "builtin.select")
        try:
            bpy.utils.unregister_tool(COATOOLS_TO_DrawPolygon)
        except:
            pass


        self.texture_preview_object = bpy.data.objects[self.texture_preview_object_name] if self.texture_preview_object_name in bpy.data.objects else None
        if self.texture_preview_object != None:
            bpy.data.objects.remove(self.texture_preview_object)
            context.view_layer.objects.active = self.edit_object
            self.edit_object.display_type = "TEXTURED"
            if len(self.edit_object.data.vertices) > 4:
                self.edit_object.data.coa_tools.hide_base_sprite = True
            else:
                self.edit_object.data.coa_tools.hide_base_sprite = False
            bpy.ops.coa_tools.reproject_sprite_texture()



    def execute(self, context):
        try:
            bpy.utils.register_tool(COATOOLS_TO_DrawPolygon, after={"builtin.select"}, separator=True, group=True)
        except:
            pass

        bpy.ops.ed.undo_push(message="Edit Mesh")
        if context.active_object == None or (context.active_object.type != "MESH" and self.mode != "DRAW_BONE_SHAPE"):
            self.report({"ERROR"},"Sprite is hidden or not selected. Cannot go in Edit Mode.")
            return{"CANCELLED"}

        if self.mode == "EDIT_MESH":
            self.edit_object, self.texture_preview_object = self.prepare_edit_object(context)
            self.edit_object_name = str(self.edit_object.name)
            self.texture_preview_object_name = str(self.texture_preview_object.name)

        #bpy.ops.wm.coa_modal() ### start coa modal mode if not running
        self.sprite_object = functions.get_sprite_object(context.active_object)
        if self.sprite_object != None:
            self.sprite_object = bpy.data.objects[self.sprite_object.name]
            
            
            self.armature = functions.get_armature(self.sprite_object)
            if self.armature != None:
                self.armature_pose_mode = self.armature.data.pose_position
                if self.mode == "EDIT_MESH":
                    self.armature.data.pose_position = "REST"
                
        
        ### get Sprite Boundaries
        if self.texture_preview_object != None and self.texture_preview_object.type == "MESH":
            self.texture_preview_object.active_shape_key_index = 0
            self.texture_preview_object.data.coa_tools.hide_base_sprite = False
            self.mesh_center , self.bounds = functions.get_bounds_and_center(self.texture_preview_object)
        
        if self.mode == "EDIT_MESH":
            #hide_base_sprite(bpy.context.active_object)
            self.edit_object.data.coa_tools.hide_base_sprite = True
            self.edit_object.active_shape_key_index = 0
            
        
        if self.mode == "DRAW_BONE_SHAPE":
            self.draw_bounds = context.scene.coa_tools.lock_to_bounds
            context.scene.coa_tools.lock_to_bounds = False
            
            bone = bpy.context.active_pose_bone
            bone.use_custom_shape_bone_size = False
            armature = bpy.context.active_object
            #bone_mat = armature.matrix_world @ bone.matrix @ bone.matrix_basis.inverted()
            bone_mat = armature.matrix_local @ bone.matrix
            bone_loc, bone_rot, bone_scale = bone_mat.decompose()
            
            if bone.custom_shape != None and bone.custom_shape.name in bpy.data.objects:
                shape_name = bone.custom_shape.name
            else:    
                shape_name = bone.name+"_custom_shape"    
                
            if self.new_shape_name != "":
                obj = bpy.data.objects[self.new_shape_name]
                me = obj.data.copy()
            else:    
                if shape_name in bpy.data.meshes:
                    me = bpy.data.meshes[shape_name]
                else:    
                    me = bpy.data.meshes.new(shape_name)
            if shape_name in bpy.data.objects and self.new_shape_name == shape_name:
                bone_shape = bpy.data.objects[shape_name]
            else:
                if shape_name in bpy.data.objects:
                    bone_shape = bpy.data.objects[shape_name]
                    bone_shape.data = me
                else:    
                    bone_shape = bpy.data.objects.new(shape_name,me)
            self.edit_object = bone_shape
            self.edit_object_name = str(self.edit_object.name)
            
            bone_shape["coa_bone_shape"] = True
            context.collection.objects.link(bone_shape)
            context.view_layer.objects.active = bone_shape
            bone_shape.select_set(True)
            bone_shape.parent = self.sprite_object
            bone_shape.name = bone.name+"_custom_shape"
            me.name = bone.name+"_custom_shape"
            
            bone_shape.name = bone.name+"_custom_shape"
            bone_shape.matrix_local = bone_mat
#            scale = 1/bone_shape.dimensions.y
#            bone_shape.scale = Vector((scale,scale,scale))
            bone_shape.show_in_front = True
            self.bone_shape = bone_shape
            self.bone = bone
            self.armature = armature
            bone.custom_shape = None#self.bone_shape
            self.display_type = self.armature.display_type
            self.armature.display_type = "WIRE"

        if self.sprite_object != None:
            self.sprite_object.coa_tools.edit_mode = "MESH"
            self.sprite_object.coa_tools.edit_mesh = True
        
        wm = context.window_manager
        
        if self.mode == "EDIT_MESH":
            self.texture_preview_object.select_set(True)
            functions.set_local_view(True)
            self.texture_preview_object.select_set(False)
        self.prev_coa_view = str(context.scene.coa_tools.view)
        context.scene.coa_tools.view = "2D"

        bpy.ops.object.mode_set(mode="EDIT")
        functions.set_active_tool(self, context, "coa_tools.draw_polygon")
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')

        args = ()
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, "WINDOW", "POST_PIXEL")
        # self.draw_handler2 = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_text, args, "WINDOW", "POST_PIXEL")
                
        bpy.ops.view3d.view_axis(type='FRONT', align_active=False, relative=False)        
        #self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)        
        #context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        return {'CANCELLED'}
    
    def draw_callback_text(self):
        obj = bpy.context.active_object
        ### draw text for edge length detection
        if self.shift and self.point_type == "EDGE":
            p1 = obj.matrix_world @ self.verts_edges_data[0]
            p2 = obj.matrix_world @ self.verts_edges_data[1]
            length = (p1-p2).magnitude

            font_id = 0
            line = str(round(length,2))
            # bgl.glEnable(bgl.GL_BLEND)
            # blf.color(font_id, 1, 1, 1, 1)

            # blf.position(font_id, self.mouse_2d_x-15, self.mouse_2d_y+30, 0)
            # blf.size(font_id, 20, 72)
            # blf.draw(font_id, line)

        if self.mode == "EDIT_MESH":
            draw_edit_mode(self,bpy.context,color=[1.0, 0.39, 0.41, 1.0],text="Edit Mesh Mode",offset=-20)
        elif self.mode == "DRAW_BONE_SHAPE":
            draw_edit_mode(self,bpy.context,color=[1.0, 0.39, 0.41, 1.0],text="Draw Bone Shape",offset=-20)

    def draw_coords(self, coords=[], color=(1.0, 1.0, 1.0, 1.0), draw_type="TRIS", shader_type="UNIFORM_COLOR", line_width=2, point_size=None):
        
        shader = gpu.shader.from_builtin(shader_type)
        gpu.state.line_width_set(line_width)
        if(point_size != None):
            gpu.state.point_size_set(point_size)
        # gpu.state.line_smooth_set(True)
        batch = batch_for_shader(shader, draw_type, {"pos": coords})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        return shader

    def coord_3d_to_2d(self, coord):
        region = bpy.context.region
        rv3d = bpy.context.space_data.region_3d
        coord_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(region, rv3d, coord)
        return coord_2d

    def draw_callback_px(self):
        obj = bpy.context.active_object

        green = [0, 1, .5, 1.0]
        blue = [.25, .2, 1, 1.0]
        red = [1, 0, 0, 1.0]
        yellow = [1, 1, 0, 1.0]

        if obj != None and obj.mode == "EDIT":

            y_offset = Vector((0, -0.0001, 0))

            vertex_vec_new = self.mouse_pos_3d

            if len(self.bounds) > 3:
                vec1 = self.coord_3d_to_2d(Vector(self.bounds[0]) + y_offset) + Vector((-1,-1))
                vec2 = self.coord_3d_to_2d(Vector(self.bounds[1]) + y_offset) + Vector((-1,1))
                vec3 = self.coord_3d_to_2d(Vector(self.bounds[3]) + y_offset) + Vector((1,1))
                vec4 = self.coord_3d_to_2d(Vector(self.bounds[2]) + y_offset) + Vector((1,-1))
                vecs = [vec1, vec2, vec3, vec4, vec1]
                self.draw_coords(coords=vecs, color=[1,.7,.5,1.0], draw_type=CONSTANTS.DRAW_LINE_STRIP, line_width=2)

            if functions.get_active_tool("EDIT_MESH") == "coa_tools.draw_polygon":
                ### draw lines and dots
                #mouse_pos_in_bounds = self.limit_cursor_by_bounds(bpy.context,self.mouse_pos_3d)
                if self.type not in ["K","C","B","R","G","S"] and self.in_view_3d:
                    vertex_vec_new = self.limit_cursor_by_bounds(bpy.context,self.mouse_pos_3d)
                    vertex_vec_new = self.snapped_vert_coord + y_offset

                    color = green
                    # bgl.glLineWidth(2)

                    if self.selected_vert_coord != None:
                        # bgl.glEnable(bgl.GL_LINE_SMOOTH)
                        vertex_vec = self.selected_vert_coord + y_offset
                        if self.point_type == "VERT":
                            color = green
                        elif self.point_type == "EDGE":
                            color = blue

                        if not self.alt:
                            p1 = self.coord_3d_to_2d(vertex_vec)
                            p2 = self.coord_3d_to_2d(vertex_vec_new)
                            self.draw_coords(coords=[p1, p2], color=color, draw_type=CONSTANTS.DRAW_LINE_STRIP, line_width=2)

                    if self.point_type == "VERT":
                        if self.alt:
                            color = red
                        else:
                            color = green
                    elif self.point_type == "EDGE":
                        color = blue
                        if self.alt:
                            color = red


                        p1 = self.coord_3d_to_2d(obj.matrix_world @ self.verts_edges_data[0] + y_offset)
                        p2 = self.coord_3d_to_2d(obj.matrix_world @ self.verts_edges_data[1] + y_offset)
                        self.draw_coords(coords=[p1,p2], color=color, draw_type=CONSTANTS.DRAW_LINE_STRIP)
                    else:
                        color = yellow

                    # draw point
                    self.draw_coords(coords=[self.coord_3d_to_2d(vertex_vec_new)], color=color, draw_type=CONSTANTS.DRAW_POINTS, point_size=8)
                    # draw intersecting edge points
                    color = yellow
                    points = []
                    for point in self.intersection_points:
                        points.append(self.coord_3d_to_2d(point))
                    self.draw_coords(coords=points, color=[0,0,0,1], draw_type=CONSTANTS.DRAW_POINTS, point_size=8)
                    self.draw_coords(coords=points, color=[1,0,.5,1], draw_type=CONSTANTS.DRAW_POINTS, point_size=6)

                # draw single vertices
                bm = bmesh.from_edit_mesh(obj.data)
                verts_loose = []
                verts_loose_selected = []
                verts_selected = []
                verts = []
                for vert in bm.verts:
                    if not vert.hide:
                        if not vert.select:
                            verts_selected.append(self.coord_3d_to_2d(obj.matrix_world @ vert.co))
                        else:
                            verts.append(self.coord_3d_to_2d(obj.matrix_world @ vert.co))

                    if not vert.hide:
                        if len(vert.link_edges) == 0:

                            if vert.select:
                                if self.contour_length == 0:
                                    verts_loose_selected.append(self.coord_3d_to_2d(obj.matrix_world @ vert.co))
                            else:
                                verts_loose.append(self.coord_3d_to_2d(obj.matrix_world @ vert.co))
                                self.draw_coords(coords=verts_loose, color=[1, 1, 1, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=8)

                self.draw_coords(coords=verts_selected, color=[0, 0, 0, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=4)
                self.draw_coords(coords=verts_selected, color=[1, 0, .5, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=2)

                self.draw_coords(coords=verts, color=[0, 0, 0, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=6)
                self.draw_coords(coords=verts, color=[0, 1, .5, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=4)

                self.draw_coords(coords=verts_loose, color=[1, 0, 0, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=8)
                self.draw_coords(coords=verts_loose_selected, color=[1, .8, .8, 1], draw_type=CONSTANTS.DRAW_POINTS, point_size=8)
            

class COATOOLS_OT_PickEdgeLength(bpy.types.Operator):
    bl_idname = "coa_tools.pick_edge_length"
    bl_label = "Pick Edge Length"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        mult = 1
        
        for edge in bm.edges:
            if edge.select:
                #scene.coa_tools.distance = (obj.matrix_world @ (edge.verts[0].co - edge.verts[1].co)).magnitude/mult# edge.calc_length()/mult        
                scene.coa_tools.distance = ((edge.verts[0].co - edge.verts[1].co)).magnitude/mult# edge.calc_length()/mult        
        bmesh.update_edit_mesh(obj.data)    
        return {"FINISHED"}
