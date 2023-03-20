import bpy
from bpy.props import StringProperty

class COATOOLS_OT_AdvancedSettings(bpy.types.Operator):
    bl_idname = "coa_tools.advanced_settings"
    bl_label = "Advanced Settings"
    bl_description = ""
    bl_options = {"REGISTER","UNDO"}
    
    obj_name: StringProperty()
    
    @classmethod
    def poll(cls, context):
        return True
    
    def check(self,context):
        return True
    
    
    def draw_shapekeys_ui(self,context,layout,ob):
        key = ob.data.shape_keys
        kb = ob.active_shape_key

        enable_edit = ob.mode != 'EDIT'
        enable_edit_value = False

        if ob.show_only_shape_key is False:
            if enable_edit or (ob.type == 'MESH' and ob.use_shape_key_edit_mode):
                enable_edit_value = True

        row = layout.row()

        rows = 2
        if kb:
            rows = 4
        row.template_list("MESH_UL_shape_keys", "", key, "key_blocks", ob, "active_shape_key_index", rows=rows)

        col = row.column()

        sub = col.column(align=True)
        sub.operator("object.shape_key_add", icon='ADD', text="").from_mix = False
        sub.operator("object.shape_key_remove", icon='REMOVE', text="").all = False
        sub.menu("MESH_MT_shape_key_specials", icon='DOWNARROW_HLT', text="")

        if kb:
            col.separator()

            sub = col.column(align=True)
            sub.operator("object.shape_key_move", icon='TRIA_UP', text="").type = 'UP'
            sub.operator("object.shape_key_move", icon='TRIA_DOWN', text="").type = 'DOWN'

            split = layout.split(percentage=0.4)
            row = split.row()
            row.enabled = enable_edit
            row.prop(key, "use_relative")

            row = split.row()
            row.alignment = 'RIGHT'

            sub = row.row(align=True)
            sub.label()  # XXX, for alignment only
            subsub = sub.row(align=True)
            subsub.active = enable_edit_value
            subsub.prop(ob, "show_only_shape_key", text="")
            sub.prop(ob, "use_shape_key_edit_mode", text="")

            sub = row.row()
            if key.use_relative:
                sub.operator("object.shape_key_clear", icon='X', text="")
            else:
                sub.operator("object.shape_key_retime", icon='RECOVER_LAST', text="")

            if key.use_relative:
                if ob.active_shape_key_index != 0:
                    row = layout.row()
                    row.active = enable_edit_value
                    row.prop(kb, "value")

                    split = layout.split()

                    col = split.column(align=True)
                    col.active = enable_edit_value
                    col.label(text="Range:")
                    col.prop(kb, "slider_min", text="Min")
                    col.prop(kb, "slider_max", text="Max")

                    col = split.column(align=True)
                    col.active = enable_edit_value
                    col.label(text="Blend:")
                    col.prop_search(kb, "vertex_group", ob, "vertex_groups", text="")
                    col.prop_search(kb, "relative_key", key, "key_blocks", text="")

            else:
                layout.prop(kb, "interpolation")
                row = layout.column()
                row.active = enable_edit_value
                row.prop(key, "eval_time")
    
    def draw(self,context):
        obj = bpy.data.objects[self.obj_name]
        layout = self.layout
        col = layout.column()
        text= obj.name + " - Sprite Settings:"
        col.label(text=text)
        
        col = layout.column()
        col.label(text="",icon="OBJECT_DATA")
        
        subrow = col.row()
        subrow.prop(obj,"show_wire")
        subrow.prop(obj,"show_all_edges")
        
        subrow = col.row()
        subrow.alignment = "LEFT"
        #subrow.prop(obj,"hide_render",text="",emboss=False)
        subrow.prop(obj,"hide_render",text="Render Sprite",icon_only=False,icon="NONE")
        
        #box = col.box()
        
        col.label(text="",icon="MESH_DATA")
        self.draw_shapekeys_ui(context,col,obj)
    
    def invoke(self,context,event):
        for obj in bpy.data.objects:
            obj.select_set(False)
        obj = bpy.data.objects[self.obj_name]
        obj.select = True
        context.scene.objects.active = obj
        
        wm = context.window_manager
        return wm.invoke_popup(self)
    
    def execute(self, context):
        return {"FINISHED"}   
