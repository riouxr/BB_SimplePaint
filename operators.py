import bpy
import gpu
import math
import random

from gpu_extras.batch import batch_for_shader

from . import utils


# =========================================================
# BRUSH OVERLAY
# =========================================================

def build_circle_coords(center, radius, segments=48):

    coords = []

    for i in range(segments):

        theta = 2.0 * math.pi * i / segments

        coords.append((
            center[0] + radius * math.cos(theta),
            center[1] + radius * math.sin(theta),
        ))

    return coords


def draw_brush_circle(operator, context):

    if operator.mouse_pos is None:
        return

    radius = operator.pixel_radius or 40.0

    if getattr(operator, "erase", False):
        color = (1.0, 0.15, 0.15, 0.9)
    elif operator.valid_hit:
        color = (0.2, 1.0, 0.4, 0.9)
    else:
        color = (1.0, 0.6, 0.1, 0.9)

    coords = build_circle_coords(
        operator.mouse_pos, radius
    )

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(
        shader, 'LINE_LOOP', {"pos": coords}
    )

    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)

    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


# =========================================================
# SHARED CONTEXT HELPERS
# =========================================================

def get_paint_target(context):

    scene = context.scene

    if scene.peoplelib_paint_mode == 'SURFACE':
        return scene.peoplelib_surface

    return None


def raycast_for_paint(context, mouse_coord, source_collection, placed_collection):

    scene = context.scene

    if scene.peoplelib_paint_mode == 'SURFACE':

        target = scene.peoplelib_surface

        if target is None:
            return None

        return utils.raycast(
            context, mouse_coord, target_object=target
        )

    def exclude(hit_obj):

        if hit_obj is None:
            return True

        return utils.is_library_object(
            hit_obj, source_collection, placed_collection
        )

    return utils.raycast(
        context, mouse_coord, exclude=exclude
    )


# =========================================================
# PAINT OPERATOR
# =========================================================

class PEOPLELIB_OT_paint(bpy.types.Operator):

    bl_idname = "peoplelib.paint"
    bl_label = "Paint Characters"
    bl_options = {'REGISTER', 'UNDO'}

    bl_description = (
        "Paint characters from the PeopleLib collection onto "
        "a surface. Hold Left Mouse to paint, release to stop, "
        "Right Mouse or Esc to exit"
    )

    erase: bpy.props.BoolProperty(
        name="Erase",
        description=(
            "Remove placed characters under the brush instead "
            "of stamping new ones"
        ),
        default=False
    )

    def __init__(self):

        self.mouse_pos = None
        self.pixel_radius = 40.0
        self.valid_hit = False
        self.painting = False
        self.timer = None
        self.draw_handler = None
        self.spatial_hash = None
        self.source_collection = None
        self.placed_collection = None

    @classmethod
    def poll(cls, context):

        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
        )

    def invoke(self, context, event):

        self.placed_collection = utils.get_placed_collection(
            context
        )

        self.source_collection = utils.get_source_collection(
            context
        )

        if not self.erase:

            if self.source_collection is None:

                self.report(
                    {'ERROR'},
                    "Collection "
                    f"'{context.scene.peoplelib_collection_name}' "
                    "not found"
                )

                return {'CANCELLED'}

            if not utils.get_character_roots(self.source_collection):

                self.report(
                    {'ERROR'},
                    "PeopleLib collection has no characters"
                )

                return {'CANCELLED'}

            if (
                context.scene.peoplelib_paint_mode == 'SURFACE'
                and context.scene.peoplelib_surface is None
            ):

                self.report(
                    {'ERROR'},
                    "Choose a Base Mesh, or switch Paint On "
                    "to 'Any Surface'"
                )

                return {'CANCELLED'}

            spacing = utils.density_to_spacing(
                context.scene.peoplelib_brush_size,
                context.scene.peoplelib_density
            )

            self.spatial_hash = utils.build_spatial_hash(
                self.placed_collection,
                max(spacing, 0.2)
            )

        self.mouse_pos = (
            event.mouse_region_x,
            event.mouse_region_y,
        )

        self.timer = context.window_manager.event_timer_add(
            0.03, window=context.window
        )

        self.draw_handler = (
            bpy.types.SpaceView3D.draw_handler_add(
                draw_brush_circle,
                (self, context),
                'WINDOW',
                'POST_PIXEL'
            )
        )

        context.window_manager.modal_handler_add(self)

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':

            self.mouse_pos = (
                event.mouse_region_x,
                event.mouse_region_y,
            )

            self.update_preview(context)

        elif event.type == 'LEFTMOUSE':

            if event.value == 'PRESS':
                self.painting = True
                self.do_action(context)

            elif event.value == 'RELEASE':
                self.painting = False

        elif event.type == 'TIMER':

            if self.painting:
                self.do_action(context)

        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:

            factor = (
                1.1
                if event.type == 'WHEELUPMOUSE'
                else 1.0 / 1.1
            )

            context.scene.peoplelib_brush_size = max(
                0.01,
                context.scene.peoplelib_brush_size * factor
            )

            self.update_preview(context)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            self.finish(context)

            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def update_preview(self, context):

        if self.erase:
            self.update_erase_preview(context)
        else:
            self.update_hit_preview(context)

    def do_action(self, context):

        if self.erase:
            self.try_erase(context)
        else:
            self.try_stamp(context)

    def update_erase_preview(self, context):

        hit = utils.raycast(context, self.mouse_pos)

        self.valid_hit = hit is not None

        if hit is not None:

            self.pixel_radius = utils.world_radius_to_pixels(
                context,
                hit[0],
                context.scene.peoplelib_brush_size
            )

    def try_erase(self, context):

        radius = self.pixel_radius or 40.0
        radius_sq = radius * radius

        to_delete = []

        for obj in list(self.placed_collection.objects):

            if obj.parent is not None:
                continue

            screen_pos = utils.location_to_screen(
                context, obj.matrix_world.translation
            )

            if screen_pos is None:
                continue

            dx = screen_pos.x - self.mouse_pos[0]
            dy = screen_pos.y - self.mouse_pos[1]

            if dx * dx + dy * dy <= radius_sq:
                to_delete.append(obj)

        for obj in to_delete:
            utils.delete_hierarchy(obj)

    def update_hit_preview(self, context):

        hit = raycast_for_paint(
            context,
            self.mouse_pos,
            self.source_collection,
            self.placed_collection
        )

        self.valid_hit = hit is not None

        if hit is not None:

            location = hit[0]

            self.pixel_radius = utils.world_radius_to_pixels(
                context,
                location,
                context.scene.peoplelib_brush_size
            )

    def try_stamp(self, context):

        hit = raycast_for_paint(
            context,
            self.mouse_pos,
            self.source_collection,
            self.placed_collection
        )

        self.valid_hit = hit is not None

        if hit is None:
            return

        center, normal, hit_obj = hit

        brush_size = context.scene.peoplelib_brush_size
        density = context.scene.peoplelib_density

        self.pixel_radius = utils.world_radius_to_pixels(
            context, center, brush_size
        )

        spacing = utils.density_to_spacing(
            brush_size, density
        )

        attempts = 1 + int(density * 6)

        for _ in range(attempts):

            dx, dy = utils.random_point_in_disk(
                self.pixel_radius
            )

            sample_coord = (
                self.mouse_pos[0] + dx,
                self.mouse_pos[1] + dy,
            )

            sample_hit = raycast_for_paint(
                context,
                sample_coord,
                self.source_collection,
                self.placed_collection
            )

            if sample_hit is None:
                continue

            location, sample_normal, sample_obj = sample_hit

            if self.spatial_hash.is_too_close(
                location, spacing
            ):
                continue

            self.stamp(context, location)

    def stamp(self, context, location):

        source_root = utils.pick_character(
            self.source_collection
        )

        if source_root is None:
            return

        new_root = utils.duplicate_character(
            context, source_root, self.placed_collection
        )

        new_root.location = location

        self.spatial_hash.add(location)

    def finish(self, context):

        if self.timer is not None:

            context.window_manager.event_timer_remove(
                self.timer
            )

            self.timer = None

        if self.draw_handler is not None:

            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handler, 'WINDOW'
            )

            self.draw_handler = None

    def cancel(self, context):

        self.finish(context)


# =========================================================
# PLACE ONE OPERATOR
# =========================================================

class PEOPLELIB_OT_place_one(bpy.types.Operator):

    bl_idname = "peoplelib.place_one"
    bl_label = "Place One Character"
    bl_options = {'REGISTER', 'UNDO'}

    bl_description = (
        "Click and hold to place a single character, "
        "drag to move it while held, release to drop it"
    )

    def __init__(self):

        self.mouse_pos = None
        self.pixel_radius = 40.0
        self.valid_hit = False
        self.state = 'WAITING'
        self.new_root = None
        self.draw_handler = None
        self.source_collection = None
        self.placed_collection = None

    @classmethod
    def poll(cls, context):

        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
        )

    def invoke(self, context, event):

        self.source_collection = utils.get_source_collection(
            context
        )

        if self.source_collection is None:

            self.report(
                {'ERROR'},
                "Collection "
                f"'{context.scene.peoplelib_collection_name}' "
                "not found"
            )

            return {'CANCELLED'}

        if not utils.get_character_roots(self.source_collection):

            self.report(
                {'ERROR'},
                "PeopleLib collection has no characters"
            )

            return {'CANCELLED'}

        if (
            context.scene.peoplelib_paint_mode == 'SURFACE'
            and context.scene.peoplelib_surface is None
        ):

            self.report(
                {'ERROR'},
                "Choose a Base Mesh, or switch Paint On "
                "to 'Any Surface'"
            )

            return {'CANCELLED'}

        self.placed_collection = utils.get_placed_collection(
            context
        )

        self.mouse_pos = (
            event.mouse_region_x,
            event.mouse_region_y,
        )

        self.draw_handler = (
            bpy.types.SpaceView3D.draw_handler_add(
                draw_brush_circle,
                (self, context),
                'WINDOW',
                'POST_PIXEL'
            )
        )

        context.window_manager.modal_handler_add(self)

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':

            self.mouse_pos = (
                event.mouse_region_x,
                event.mouse_region_y,
            )

            self.update_preview(context)

            if self.state == 'DRAGGING' and self.new_root:

                hit = raycast_for_paint(
                    context,
                    self.mouse_pos,
                    self.source_collection,
                    self.placed_collection
                )

                if hit is not None:
                    self.new_root.location = hit[0]

        elif event.type == 'LEFTMOUSE':

            if event.value == 'PRESS' and self.state == 'WAITING':

                self.start_drag(context)

            elif (
                event.value == 'RELEASE'
                and self.state == 'DRAGGING'
            ):

                self.finish(context)

                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            if self.new_root is not None:
                utils.delete_hierarchy(self.new_root)

            self.finish(context)

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def update_preview(self, context):

        hit = raycast_for_paint(
            context,
            self.mouse_pos,
            self.source_collection,
            self.placed_collection
        )

        self.valid_hit = hit is not None

        if hit is not None:

            self.pixel_radius = utils.world_radius_to_pixels(
                context,
                hit[0],
                context.scene.peoplelib_brush_size * 0.3
            )

    def start_drag(self, context):

        hit = raycast_for_paint(
            context,
            self.mouse_pos,
            self.source_collection,
            self.placed_collection
        )

        if hit is None:

            self.report(
                {'WARNING'},
                "No surface under the cursor"
            )

            return

        location, normal, hit_obj = hit

        source_root = utils.pick_character(
            self.source_collection
        )

        if source_root is None:
            return

        self.new_root = utils.duplicate_character(
            context, source_root, self.placed_collection
        )

        self.new_root.location = location

        self.state = 'DRAGGING'

    def finish(self, context):

        if self.draw_handler is not None:

            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handler, 'WINDOW'
            )

            self.draw_handler = None

    def cancel(self, context):

        self.finish(context)


classes = (
    PEOPLELIB_OT_paint,
    PEOPLELIB_OT_place_one,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
