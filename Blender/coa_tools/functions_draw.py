import bpy
import bgl,blf

def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

def draw_edit_mode(self,context,color=[0.41, 0.38, 1.0, 1.0],text="Edit Shapekey Mode",offset=0):
    region = context.region
    x = region.width
    y = region.height
    
    scale = x / 1200
    scale = clamp(scale,.5,1.5)
    
    r_offset = 0
    if context.preferences.system.use_region_overlap:
        r_offset = context.area.regions[1].width

    ### draw box behind text
    b_width = int(240*scale)
    b_height = int(36*scale)
    
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(color[0],color[1],color[2],color[3])
    
    bgl.glBegin(bgl.GL_QUADS)
    bgl.glVertex2i(x-b_width, 0)
    bgl.glVertex2i(x, 0)
    bgl.glVertex2i(x, b_height)
    bgl.glVertex2i(x-b_width, b_height)
    bgl.glVertex2i(x-b_width, 0) 
    bgl.glEnd()
    
    ### draw edit type
    font_id = 0  # XXX, need to find out how best to get this.
    bgl.glColor4f(0.041613, 0.041613, 0.041613, 1.000000)
    text_offset = int((220+offset)*scale)
    text_y_offset = int(11 * scale)
    blf.position(font_id, x-text_offset, text_y_offset, 0)
    blf.size(font_id, 20, int(72*scale))
    blf.draw(font_id, text)
    
    ### draw viewport outline
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(color[0],color[1],color[2],color[3])
    bgl.glLineWidth(4)

    bgl.glBegin(bgl.GL_LINE_STRIP)
    bgl.glVertex2i(r_offset, 0)
    bgl.glVertex2i(r_offset+x, 0)
    bgl.glVertex2i(r_offset+x, y)
    bgl.glVertex2i(r_offset+0, y)
    bgl.glVertex2i(r_offset, 0)

    bgl.glEnd()

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)