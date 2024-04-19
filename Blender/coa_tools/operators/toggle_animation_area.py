import bpy
from bpy.props import EnumProperty

class COATOOLS_OT_ToggleAnimationArea(bpy.types.Operator):
    bl_idname = "coa_tools.toggle_animation_area"
    bl_label = "Toggle Animation Area"
    bl_description = "Toggle Animation Editors"
    bl_options = {"REGISTER"}
    
    mode: EnumProperty(items=(("TOGGLE","TOGGLE","TOGGLE"),("UPDATE","UPDATE","UPDATE")),default="TOGGLE")
    
    black_list = ["__module__","type","has_ghost_curves"]
    editor = "DOPESHEET_EDITOR"
    
    @classmethod
    def poll(cls, context):
        return True
    
    
    def split_area(self,context,type="DOPESHEET_EDITOR",direction="HORIZONTAL",reference_area=None,ratio=0.7):
        start_areas = context.screen.areas[:]

        area = None
        if reference_area != None:
            area = reference_area
        else:    
            area = context.area

        with bpy.context.temp_override(area=area): 
            bpy.ops.screen.area_split(direction=direction,factor=ratio)    

        for area in context.screen.areas:
            if area not in start_areas:
                area.type = type
        return area
    
    def join_area(self,context,area1,area2):
        type = str(area2.type)
        x1=0
        y1=0
        x2=0
        y2=0

        x1 = area1.x
        y1 = area1.y
        x2 = area2.x
        y2 = area2.y

        bpy.ops.screen.area_join(min_x=x2,min_y=y2,max_x=x1,max_y=y1)       
        area2.type = "NLA_EDITOR"    
        area2.type = type
        
    def get_areas(self,context):
        view_3d = None
        dopesheet_editor = None
        graph_editor = None
        
        dopesheet_editors = []
        graph_editors = []
        
        x = 0
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                view_3d = area
            elif area.type in ["NLA_EDITOR","DOPESHEET_EDITOR"]:#== self.editor:
                dopesheet_editors.append(area)
                x += area.width
            elif area.type == "GRAPH_EDITOR":
                x += area.width
                graph_editors.append(area)
        
        for d in dopesheet_editors:
            for g in graph_editors:
                if g.height == d.height and (((g.width + d.width + 1) == view_3d.width)):
                    dopesheet_editor = d
                    graph_editor = g
        return [view_3d, dopesheet_editor, graph_editor]          
    
    def store_object_as_dict(self,object):
        str_dict = {}
        for key in dir(object):
            value = getattr(object,key)
            if type(value) in [str, int, float, bool] and key not in self.black_list:
                str_dict[key] = value
        return str(str_dict)
    def store_data_in_scene(self,context,area_dopesheet_editor,area_graph_editor):
        if area_dopesheet_editor.type == "DOPESHEET_EDITOR":
            editor = "DOPESHEET_EDITOR"
        elif area_dopesheet_editor.type == "NLA_EDITOR":
            editor = "NLA_EDITOR"
            
        settings = editor + "_SETTINGS"
        settings2 = editor + "_SETTINGS2"
        context.scene[settings] = self.store_object_as_dict(area_dopesheet_editor.spaces[0])
        context.scene[settings2] = self.store_object_as_dict(area_dopesheet_editor.spaces[0].dopesheet)
        
        context.scene["GRAPH_EDITOR_SETTINGS"] = self.store_object_as_dict(area_graph_editor.spaces[0])
        context.scene["GRAPH_EDITOR_SETTINGS2"] = self.store_object_as_dict(area_graph_editor.spaces[0].dopesheet)
    
    def restore_editor_settings(self,context,editor,editor_settings_key):
        if editor_settings_key in context.scene:
                settings = eval(context.scene[editor_settings_key])
                for key in settings:
                    setattr(editor,key,settings[key])
    
    def create_editor_areas(self,context,area_dopesheet_editor=None,area_graph_editor=None):
        if area_dopesheet_editor == None:
            area_dopesheet_editor = self.split_area(context,type=self.editor,direction="HORIZONTAL",reference_area=context.area,ratio=0.7)
        else:
            self.store_data_in_scene(context,area_dopesheet_editor,area_graph_editor)
            area_dopesheet_editor.type = self.editor
        
        if area_graph_editor == None:
            area_graph_editor = self.split_area(context,type="GRAPH_EDITOR",direction="VERTICAL",reference_area=area_dopesheet_editor,ratio=0.7)
        
        settings = self.editor + "_SETTINGS"
        settings2 = self.editor + "_SETTINGS2"
        
        self.restore_editor_settings(context,area_dopesheet_editor.spaces[0],settings)
        self.restore_editor_settings(context,area_dopesheet_editor.spaces[0].dopesheet,settings2)
        self.restore_editor_settings(context,area_graph_editor.spaces[0],"GRAPH_EDITOR_SETTINGS")
        self.restore_editor_settings(context,area_graph_editor.spaces[0].dopesheet,"GRAPH_EDITOR_SETTINGS2")
        return area_dopesheet_editor, area_graph_editor
    
    def remove_editor_areas(self,context,area_dopesheet_editor,area_graph_editor,area_3d):
        self.store_data_in_scene(context,area_dopesheet_editor,area_graph_editor)
        
        self.join_area(context,area_graph_editor,area_dopesheet_editor)
        self.join_area(context,area_dopesheet_editor,area_3d)
        
    def execute(self, context):
        if context.scene.coa_tools.nla_mode == "ACTION":
            self.editor = "DOPESHEET_EDITOR"
        elif context.scene.coa_tools.nla_mode == "NLA":
            self.editor = "NLA_EDITOR"
            
        
        area_3d = None
        area_dopesheet_editor = None
        area_graph_editor = None
        
        area_3d, area_dopesheet_editor, area_graph_editor = self.get_areas(context)
                    
        ### create animation area
        if area_dopesheet_editor == None and area_graph_editor == None:
            if self.mode == "TOGGLE":
                self.create_editor_areas(context)    
            
        ### join animation area        
        elif area_dopesheet_editor != None and area_graph_editor != None:
            if self.mode == "TOGGLE":
                self.remove_editor_areas(context,area_dopesheet_editor,area_graph_editor,area_3d)
            elif self.mode == "UPDATE":
                self.create_editor_areas(context,area_dopesheet_editor,area_graph_editor)                
        
        return {"FINISHED"}
        