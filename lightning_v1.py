bl_info = {
    "name": "Lightning Strike v1",
    "category": "Object",
}

import bpy
import bmesh
import random

class ObjectLightningStrike(bpy.types.Operator):
    """Object Lightning Strike"""
    bl_idname = "object.lightning_strike"
    bl_label = "Lightning Strike"
    bl_options = {'REGISTER', 'UNDO'}

    # Total height of the lightning strike.
    height = bpy.props.IntProperty(name="Height", default=20, min=2)

    # Seed that determines the shape of the strike.
    shape_seed = bpy.props.IntProperty(name="Shape Seed", default=0, min=0)

    # Distance between points, applied to x, y, and z coordinates.
    step_size = bpy.props.IntProperty(name="Step Size", default=1, min=1)

    # Number of branches on each level.
    num_branches = bpy.props.IntProperty(name="Branches", default=1, min=0)

    # Number of times branches will sprout sub-branches
    num_levels = bpy.props.IntProperty(name="Levels", default=1, min=1)

    # Animation seed.
    animation_seed = bpy.props.IntProperty(name="Animation Seed", default=0, min=0)

    # Number of times the bolt will flash.  The last flash will always be the brightest.
    num_flashes = bpy.props.IntProperty(name="Flashes", default=1, min=1)

    # The list of random (frame, intensity) tuples from which keyframes will be created
    intensities = None

    # Populates self.intensities with random keyframe information.
    # These will be applied to all generated objects.
    def gen_flash_frames(self):
        random.seed(self.animation_seed)

        self.intensities = []

        frame = 0
        self.intensities.append((frame, 0.0))
        for i in range(0, self.num_flashes - 1):
            frame = frame + random.randrange(2, 6, 1) # flash peaks here
            self.intensities.append((frame, random.uniform(1.0, 1.5)))

            frame = frame + random.randrange(2, 6, 1) # flash fades here
            self.intensities.append((frame, random.uniform(0.0, 0.4)))

        # Make last flash the highest intensity
        frame = frame + random.randrange(2, 6, 1) # flash peaks here
        self.intensities.append((frame, 2.0))

        frame = frame + random.randrange(2, 6, 1) # flash fades here
        self.intensities.append((frame, 0))


    # Generates a random curve with the origin at (init_x, init_y, init_z)
    # and extending down to final_z.
    # final_z must be smaller than init_z.
    def gen_curve(self, context, name, init_x, init_y, init_z, final_z):
        scene = context.scene

        # create the Curve Datablock
        curveData = bpy.data.curves.new(name, type='CURVE')
        curveData.dimensions = '3D'
        curveData.resolution_u = 2 # this determines lightning thickness

        curve = curveData.splines.new('BEZIER')

        # There's already one point, and we want it at the current root
        p0 = curve.bezier_points[0]
        p0.co = (init_x, init_y, init_z)
        # 'VECTOR' makes curves sharp
        p0.handle_right_type = 'VECTOR'
        p0.handle_left_type = 'VECTOR'

        (x, y, current_z) = (init_x, init_y, init_z)
        while True:
            if current_z <= final_z:
                break

            rz = random.uniform(0, 1)
            current_z = current_z - (self.step_size / 2) * rz
            if current_z < final_z:
                current_z = final_z
            i = len(curve.bezier_points)
            curve.bezier_points.add(1)
            pn = curve.bezier_points[i]
            rx = random.uniform(-1, 1)
            ry = random.uniform(-1, 1)
            x = x + self.step_size * rx
            y = y + self.step_size * ry

            pn.co = (x, y, current_z)
            pn.handle_right_type = 'VECTOR'
            pn.handle_left_type = 'VECTOR'

        return curveData


    # Creates the CLOUDS based texture used for animating the main lighnig bolt.
    # Animation keyframes applied from the self.intensities array.
    def texture_main_strike(self, context, curve_obj):
        # Material
        material = bpy.data.materials.new(name="lightning_core")
        material.use_transparency = True
        material.alpha = 0
        material.emit = 0 # default must be 0 or it will light the scene even when lightning is invisible.
        material.specular_intensity = 0
        curve_obj.data.materials.append(material)

        # Texture with keyframes
        texture = bpy.data.textures.new('BlendTex', type = 'CLOUDS')

        cur_frame = bpy.context.scene.frame_current
        for frame, intensity in self.intensities:
            cur_frame = cur_frame + frame
            texture.intensity = intensity
            texture.keyframe_insert(data_path="intensity", frame=cur_frame)

        texture_slot = material.texture_slots.add()
        texture_slot.use_map_emit = True
        texture_slot.use_map_alpha = True
        texture_slot.use_map_color_diffuse = False
        texture_slot.texture = texture


    # Creates the VERTICAL GRADIENT based texture used for animating the lighnig strike branches.
    # Animation keyframes applied from the self.intensities array.
    def texture_branch(self, context, curve_obj):
        # Material
        material = bpy.data.materials.new(name="lightning_branch")
        material.use_transparency = True
        material.alpha = 0
        material.emit = 0
        material.specular_intensity = 0
        curve_obj.data.materials.append(material)

        # Texture with keyframes
        texture = bpy.data.textures.new('BlendTex', type = 'BLEND')
        texture.progression = 'LINEAR'
        texture.use_flip_axis = 'VERTICAL'
        texture.use_color_ramp = True

        cur_frame = bpy.context.scene.frame_current
        for frame, intensity in self.intensities:
            cur_frame = cur_frame + frame
            texture.intensity = intensity
            texture.keyframe_insert(data_path="intensity", frame=cur_frame)

        texture_slot = material.texture_slots.add()
        texture_slot.use_map_emit = True
        texture_slot.use_map_alpha = True
        texture_slot.use_map_color_diffuse = False
        texture_slot.texture_coords = 'UV'
        texture_slot.texture = texture


    #  Generates all levels of lightning branches recursively.
    def make_branches(self, context, root_curve, num_levels, num_level_branches, final_z):
        result_branches = []

        if num_levels == 0 or num_level_branches == 0:
            return result_branches

        num_branches = min(num_level_branches, len(root_curve.splines[0].bezier_points))
        branch_roots = random.sample(list(root_curve.splines[0].bezier_points), num_branches)
        for root in branch_roots:
            branch_height = (root.co.z - final_z) * random.uniform(0.3, 0.7)
            branch_final_z = root.co.z - branch_height
            if root.co.z <= branch_final_z:
                print("Skipping branch without height")
                continue

            branch_curve = self.gen_curve(context, "branch", root.co.x, root.co.y, root.co.z, branch_final_z)
            curve_obj = bpy.data.objects.new("branch", branch_curve)
            curve_obj.data.fill_mode = 'FULL'
            curve_obj.data.use_fill_deform = True
            curve_obj.data.bevel_depth = 0.06
            curve_obj.data.bevel_resolution = 2

            children = self.make_branches(context, branch_curve, num_levels - 1, num_level_branches, final_z)

            scn = bpy.context.scene
            scn.objects.link(curve_obj)
            scn.objects.active = curve_obj
            curve_obj.select = True
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

            # UV unwrapping is done manually, which is slightly
            # more convenient than calling a built-in function, like "project from view".
            # This arranges vertices verticaly, as they appear in the lightning branch,
            # so that they match the vertical gradient used to animate the flash.
            # The horizontal location does not matter, so the middle of the
            # UV map (u=0.5) is as good a place as any.

            bpy.ops.object.convert(target='MESH', keep_original=False)
            bpy.context.object.data.uv_textures.new("branch_gradient")
            bm = bmesh.new()
            bm.from_mesh(bpy.context.object.data)

            bm.faces.ensure_lookup_table()
            uv_layer = bm.loops.layers.uv[0]
            uv_scale = self.height
            for face in bm.faces:
                vert_i = 0
                for vert in face.verts:
                    face.loops[vert_i][uv_layer].uv = (0.5, (vert.co.z - final_z) / uv_scale)
                    vert_i = vert_i + 1
            bm.to_mesh(bpy.context.object.data)
            bm.free()

            # Join all levels into a single object to avoid clutter.
            for child in children:
                child.select = True
            scn.objects.active = bpy.context.object
            bpy.ops.object.join()

            curve_obj.select = False
            result_branches.append(curve_obj)
        return result_branches


    def execute(self, context):
        self.gen_flash_frames()

        random.seed(self.shape_seed)

        # Make sure nothing is selected initially because this script uses the join operation,
        # which will join all selected objects into one.
        bpy.ops.object.select_all(action='DESELECT')

        # Make lightning start at the current cursor position.
        (x, y, z) = context.scene.cursor_location
        start_z = z
        final_z = start_z - self.height

        # Main strike curve
        main_curve = self.gen_curve(context, "main_strike", x, y, z, final_z)
        curve_obj = bpy.data.objects.new('main_strike', main_curve)
        curve_obj.data.fill_mode = 'FULL'
        curve_obj.data.use_fill_deform = True
        curve_obj.data.bevel_depth = 0.21
        curve_obj.data.bevel_resolution = 2
        self.texture_main_strike(context, curve_obj)

        # attach to scene and validate context
        scn = bpy.context.scene
        scn.objects.link(curve_obj)
        scn.objects.active = curve_obj

        ## Make branches
        branches = self.make_branches(context, main_curve, self.num_levels, self.num_branches, final_z)
        for branch in branches:
            self.texture_branch(context, branch)

        # TODO: Join all branches into a single object to avoid clutter.
        # TODO: Create a group for lightning objects for easier manipulation.

        # Setting origin to the root of the strike makes it easy to rotate.
        curve_obj.select = True
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        curve_obj.select = False

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ObjectLightningStrike.bl_idname)


def register():
    bpy.utils.register_class(ObjectLightningStrike)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ObjectLightningStrike)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
