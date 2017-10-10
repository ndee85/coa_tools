import bpy
import math
import random

class RhubarbOperator(bpy.types.Operator):
    bl_idname = "action.rhubarb_lipsync"
    bl_label = "Rhubarb Lipsync"
    bl_options = {'REGISTER', 'UNDO'}

    filename = bpy.props.StringProperty(
        name="Rhubarb file",
        description="File with Lipsync data created by Rhubarb",
        subtype='FILE_PATH'
    )

    startAtCurrentFrame = bpy.props.BoolProperty(
        name="Start at current frame",
        description="Add keyframes starting at current frame."
    )

    fps = 24

    shapes = {
        'A': 0,
        'B': 1,
        'C': 2,
        'D': 3,
        'E': 4,
        'F': 5,
        'G': 6,
        'H': 7,
        'X': 8,
    }

    def execute(self, context):
        self.fps = bpy.context.scene.render.fps
        if self.filename:
            data = self.parseRhubarbFile(self.filename)
            self.createKeyframes(data)

        return {'FINISHED'}

    def parseRhubarbFile(self, filename):
        data = []

        with open(filename) as lines:
            for line in lines:
                r = line.split()
                data.append((round(float(r[0]) * self.fps), self.shapes[r[1]]))

        return data

    def createKeyframes(self, data):
        length = data[len(data)-1][0]

        frame_current = bpy.context.scene.frame_current
        frame_end = bpy.context.scene.frame_end

        f = 0

        if self.startAtCurrentFrame and frame_end < frame_current + length + 1:
            bpy.context.scene.frame_end = frame_current + length + 1
            f = frame_current
        elif frame_end < length + 1:
            bpy.context.scene.frame_end = length + 1

        sprite = bpy.context.scene.objects.active

        if sprite:
            for key in data:
                sprite.coa_sprite_frame = key[1]
                sprite.keyframe_insert(data_path='["coa_sprite_frame"]', frame=(f + key[0]+1))


def register():
    bpy.utils.register_class(RhubarbOperator)

if __name__ == "__main__":
    register()