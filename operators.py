import bpy
import gpu
import math

from mathutils import Vector
from gpu_extras.batch import batch_for_shader

from . import preview, utils


# =========================================================
# VIEWPORT NAVIGATION
# =========================================================

NAVIGATION_EVENT_TYPES = {
    'MIDDLEMOUSE',
    'TRACKPADPAN',
    'TRACKPADZOOM',
    'MOUSEROTATE',
    'MOUSESMARTZOOM',
}

NAVIGATION_ALT_TYPES = {
    'LEFTMOUSE',
    'RIGHTMOUSE',
    'MOUSEMOVE',
    'WHEELUPMOUSE',
    'WHEELDOWNMOUSE',
}


def is_navigation_event(event):

    """Events the viewport has to keep while a brush is running.

    Alt is what the Industry Compatible keymap and the emulated
    3-button mouse use for orbit, pan and zoom, so an Alt-held event
    belongs to the viewport, not to the brush. Middle mouse and the
    trackpad gestures cover the default keymap.
    """

    if event.type in NAVIGATION_EVENT_TYPES:
        return True

    return event.alt and event.type in NAVIGATION_ALT_TYPES


# =========================================================
# UNDO
# =========================================================

def push_start_undo(context):

    """Snapshot the scene before the tool changes anything.

    Each stroke pushes its own step, but the *first* Ctrl+Z needs a
    step holding the pre-tool state to land on. Without one it falls
    back to whatever unrelated step happened to be on the stack when
    the tool was started, so the undo appears to skip the painting and
    revert earlier work instead.
    """

    bpy.ops.ed.undo_push(message="Simple Paint Start")


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

def raycast_for_paint(context, mouse_coord, source_collection, placed_collection):

    scene = context.scene

    if scene.simplepaint_paint_mode == 'SURFACE':

        targets = utils.get_surface_targets(
            context, source_collection, placed_collection
        )

        if not targets:
            return None

        return utils.raycast_targets(
            context, mouse_coord, targets
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


def validate_prerequisites(operator, context):

    source_collection = utils.get_source_collection(context)

    if source_collection is None:

        operator.report(
            {'ERROR'},
            "Pick a source Collection in the Simple Paint panel"
        )

        return None

    if not utils.get_item_roots(source_collection):

        operator.report(
            {'ERROR'},
            "Collection has no items"
        )

        return None

    if context.scene.simplepaint_paint_mode == 'SURFACE':

        placed_collection = utils.get_placed_collection(context)

        targets = utils.get_surface_targets(
            context, source_collection, placed_collection
        )

        if not targets:

            operator.report(
                {'ERROR'},
                "Select one or more surface objects first, "
                "or switch Paint On to 'Any Surface'"
            )

            return None

    return source_collection


# =========================================================
# PAINT OPERATOR
# =========================================================

class SIMPLEPAINT_OT_paint(bpy.types.Operator):

    bl_idname = "simplepaint.paint"
    bl_label = "Paint Items"

    # No 'UNDO': a modal tool that runs for many strokes would push a
    # single step covering everything. Each stroke pushes its own undo
    # step instead (see push_undo), so Ctrl+Z steps back one stroke at
    # a time both during the tool and after exiting it.
    bl_options = {'REGISTER'}

    bl_description = (
        "Paint items from the source collection onto a surface. "
        "Hold Left Mouse to paint, release to stop, E to toggle "
        "Erase, F to resize the brush, Ctrl+Z to undo a stroke, "
        "Tab to switch to Place One, Right Mouse or Esc to exit"
    )

    erase: bpy.props.BoolProperty(
        name="Erase",
        description=(
            "Remove placed items under the brush instead "
            "of stamping new ones"
        ),
        default=False
    )

    @classmethod
    def poll(cls, context):

        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
        )

    def invoke(self, context, event):

        self.mouse_pos = None
        self.pixel_radius = 40.0
        self.valid_hit = False
        self.painting = False
        self.timer = None
        self.draw_handler = None
        self.spatial_hash = None
        self.source_collection = None
        self.placed_collection = None

        self.resizing = False
        self.resize_start_mouse_x = None
        self.resize_start_size = None
        self.resize_start_pixel_radius = None

        self.spacing_adjust = False
        self.preview_was_on = False
        self.stroke_changed = False

        self.placed_collection = utils.get_placed_collection(
            context
        )

        self.source_collection = utils.get_source_collection(
            context
        )

        if not self.erase:

            self.source_collection = validate_prerequisites(
                self, context
            )

            if self.source_collection is None:
                return {'CANCELLED'}

        self.rebuild_hash(context)

        push_start_undo(context)

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

        self.update_header(context)

        return {'RUNNING_MODAL'}

    def rebuild_hash(self, context):

        # Rebuilt from the live collection rather than mutated, so
        # erasing items (or deleting them in the outliner) frees that
        # area up to be painted again instead of leaving stale points
        # that keep rejecting every new sample there.
        self.spatial_hash = utils.build_spatial_hash(
            self.placed_collection,
            context.scene.simplepaint_spacing
        )

    def push_undo(self, context, label):

        if not self.stroke_changed:
            return

        self.stroke_changed = False

        bpy.ops.ed.undo_push(message=label)

    def run_undo(self, context, redo=False):

        self.painting = False
        self.stroke_changed = False

        try:

            if redo:
                bpy.ops.ed.redo()
            else:
                bpy.ops.ed.undo()

        except RuntimeError:
            return

        # Undo swaps datablocks out, so every reference held across
        # the call has to be looked up again rather than reused.
        self.placed_collection = utils.get_placed_collection(
            context
        )

        self.source_collection = utils.get_source_collection(
            context
        )

        self.rebuild_hash(context)

        preview.clear_cache()

    def update_header(self, context):

        mode = "Erase" if self.erase else "Paint"

        if self.spacing_adjust:

            spacing = context.scene.simplepaint_spacing

            context.area.header_text_set(
                f"BB Simple Paint [Spacing]  |  Wheel: Spacing "
                f"= {spacing:.3f}  |  Release D: back to {mode}"
            )

            return

        context.area.header_text_set(
            f"BB Simple Paint [{mode}]  |  LMB: "
            f"{'Erase' if self.erase else 'Paint'}  "
            "|  E: Toggle Erase  |  F: Resize Brush  |  "
            "D+Wheel: Spacing  |  Shift+F: Flood  |  "
            "Wheel: Brush Size  |  Tab: Place One  |  "
            "RMB/Esc: Exit"
        )

    def modal(self, context, event):

        context.area.tag_redraw()

        if self.resizing:
            return self.modal_resize(context, event)

        if is_navigation_event(event):

            # A stroke can't survive the viewport moving under it.
            self.painting = False

            return {'PASS_THROUGH'}

        if event.type == 'Z' and event.ctrl and event.value == 'PRESS':

            self.run_undo(context, redo=event.shift)

            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':

            self.mouse_pos = (
                event.mouse_region_x,
                event.mouse_region_y,
            )

            self.update_preview(context)

        elif event.type == 'LEFTMOUSE':

            if event.value == 'PRESS':

                # The dots have done their job once real items start
                # landing, and leaving them on just clutters the
                # surface being painted.
                if context.scene.simplepaint_show_preview:
                    context.scene.simplepaint_show_preview = False

                # Don't let a later D release resurrect it.
                self.preview_was_on = False

                # Pick up anything erased or deleted since the last
                # stroke before laying down new items.
                self.rebuild_hash(context)

                self.painting = True
                self.do_action(context)

            elif event.value == 'RELEASE':

                self.painting = False

                self.push_undo(
                    context,
                    "Erase Items" if self.erase else "Paint Items"
                )

        elif event.type == 'TIMER':

            if self.painting:
                self.do_action(context)

        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:

            factor = (
                1.1
                if event.type == 'WHEELUPMOUSE'
                else 1.0 / 1.1
            )

            if self.spacing_adjust:

                context.scene.simplepaint_spacing = max(
                    0.001,
                    context.scene.simplepaint_spacing * factor
                )

                self.rebuild_hash(context)
                self.update_header(context)

            else:

                context.scene.simplepaint_brush_size = max(
                    0.01,
                    context.scene.simplepaint_brush_size * factor
                )

            self.update_preview(context)

        elif event.type == 'D':

            if event.value == 'PRESS' and not self.spacing_adjust:

                self.spacing_adjust = True
                self.painting = False

                self.preview_was_on = (
                    context.scene.simplepaint_show_preview
                )

                context.scene.simplepaint_show_preview = True

                self.update_header(context)

            elif event.value == 'RELEASE' and self.spacing_adjust:

                self.spacing_adjust = False

                context.scene.simplepaint_show_preview = (
                    self.preview_was_on
                )

                self.update_header(context)

        elif event.type == 'E' and event.value == 'PRESS':

            self.erase = not self.erase
            self.painting = False
            self.update_preview(context)
            self.update_header(context)

        elif event.type == 'F' and event.value == 'PRESS':

            if event.shift:

                bpy.ops.simplepaint.flood()

                # Flood just added a pile of items; resync so the
                # brush respects them.
                self.rebuild_hash(context)

            else:

                self.start_resize(context)

        elif event.type == 'TAB' and event.value == 'PRESS':

            self.finish(context)

            bpy.ops.simplepaint.place_one('INVOKE_DEFAULT')

            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            self.finish(context)

            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def start_resize(self, context):

        self.resizing = True
        self.painting = False
        self.resize_start_mouse_x = None
        self.resize_start_size = context.scene.simplepaint_brush_size
        self.resize_start_pixel_radius = self.pixel_radius or 40.0

    def modal_resize(self, context, event):

        if event.type == 'MOUSEMOVE':

            self.mouse_pos = (
                event.mouse_region_x,
                event.mouse_region_y,
            )

            if self.resize_start_mouse_x is None:
                self.resize_start_mouse_x = event.mouse_x

            delta = event.mouse_x - self.resize_start_mouse_x

            new_pixel_radius = max(
                2.0, self.resize_start_pixel_radius + delta
            )

            ratio = new_pixel_radius / max(
                self.resize_start_pixel_radius, 1.0
            )

            context.scene.simplepaint_brush_size = max(
                0.01, self.resize_start_size * ratio
            )

            self.pixel_radius = new_pixel_radius

            return {'RUNNING_MODAL'}

        if (
            event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER', 'F'}
            and event.value == 'PRESS'
        ):

            self.resizing = False
            self.update_preview(context)

            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

            context.scene.simplepaint_brush_size = (
                self.resize_start_size
            )

            self.resizing = False
            self.update_preview(context)

            return {'RUNNING_MODAL'}

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
                context.scene.simplepaint_brush_size
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

        if not to_delete:
            return

        for obj in to_delete:
            utils.delete_hierarchy(obj)

        self.stroke_changed = True

        # Free the erased area back up for painting.
        self.rebuild_hash(context)

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
                context.scene.simplepaint_brush_size
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

        brush_size = context.scene.simplepaint_brush_size
        spacing = context.scene.simplepaint_spacing

        self.pixel_radius = utils.world_radius_to_pixels(
            context, center, brush_size
        )

        # Spacing is absolute world distance, so the brush only
        # decides how much area a tick covers, never how packed the
        # result is. Sample proportionally to how many items could
        # fit under the brush, so a bigger brush fills its larger
        # area at the same density instead of thinning out.
        capacity = (
            math.pi * brush_size * brush_size
        ) / (spacing * spacing)

        attempts = max(1, min(int(capacity) + 1, 40))

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

            self.stamp(context, location, sample_normal)

    def stamp(self, context, location, normal):

        source_root = utils.pick_item(
            self.source_collection
        )

        if source_root is None:
            return

        new_root = utils.duplicate_item(
            context, source_root, self.placed_collection
        )

        random_quat = utils.roll_random_quat(context)
        scale_mult = utils.roll_scale_mult(context)

        new_root.matrix_world = utils.item_transform(
            context, source_root, location, normal,
            random_quat, scale_mult
        )

        self.spatial_hash.add(location)

        self.stroke_changed = True

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

        context.area.header_text_set(None)

    def cancel(self, context):

        self.finish(context)


# =========================================================
# PLACE ONE OPERATOR
# =========================================================

class SIMPLEPAINT_OT_place_one(bpy.types.Operator):

    bl_idname = "simplepaint.place_one"
    bl_label = "Place One"

    # Same reasoning as the paint tool: each drop pushes its own undo
    # step so Ctrl+Z removes one item at a time.
    bl_options = {'REGISTER'}

    bl_description = (
        "Click and hold to place an item, drag to move it "
        "while held, release to drop it. Repeat to place more, "
        "Ctrl+Z to undo a placement, Tab to switch to Paint, "
        "Right Mouse or Esc to exit"
    )

    @classmethod
    def poll(cls, context):

        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
        )

    def invoke(self, context, event):

        self.mouse_pos = None
        self.pixel_radius = 40.0
        self.valid_hit = False
        self.state = 'WAITING'
        self.new_root = None
        self.draw_handler = None
        self.source_collection = None
        self.placed_collection = None
        self.placed_count = 0

        self.item_source_root = None
        self.item_random_quat = None
        self.item_scale_mult = Vector((1.0, 1.0, 1.0))

        self.source_collection = validate_prerequisites(
            self, context
        )

        if self.source_collection is None:
            return {'CANCELLED'}

        self.placed_collection = utils.get_placed_collection(
            context
        )

        push_start_undo(context)

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

        context.area.header_text_set(
            "BB Simple Paint [Place One]  |  LMB: place & drag, "
            "release to drop, repeat for more  |  "
            "Shift+F: Flood  |  Tab: Paint  |  RMB/Esc: Exit"
        )

        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        context.area.tag_redraw()

        if is_navigation_event(event) and self.state != 'DRAGGING':
            return {'PASS_THROUGH'}

        if event.type == 'Z' and event.ctrl and event.value == 'PRESS':

            # Undoing mid-drag would leave a dangling reference to an
            # item the undo may have just removed.
            if self.state == 'DRAGGING' and self.new_root is not None:

                utils.delete_hierarchy(self.new_root)
                self.new_root = None
                self.state = 'WAITING'

            try:

                if event.shift:
                    bpy.ops.ed.redo()
                else:
                    bpy.ops.ed.undo()

            except RuntimeError:
                return {'RUNNING_MODAL'}

            self.placed_collection = utils.get_placed_collection(
                context
            )

            self.source_collection = utils.get_source_collection(
                context
            )

            preview.clear_cache()

            return {'RUNNING_MODAL'}

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

                    location, normal, hit_obj = hit

                    self.new_root.matrix_world = (
                        utils.item_transform(
                            context,
                            self.item_source_root,
                            location,
                            normal,
                            self.item_random_quat,
                            self.item_scale_mult
                        )
                    )

        elif event.type == 'LEFTMOUSE':

            if event.value == 'PRESS' and self.state == 'WAITING':

                self.start_drag(context)

            elif (
                event.value == 'RELEASE'
                and self.state == 'DRAGGING'
            ):

                self.placed_count += 1
                self.new_root = None
                self.state = 'WAITING'

                bpy.ops.ed.undo_push(message="Place Item")

        elif event.type == 'TAB' and event.value == 'PRESS':

            if self.new_root is not None:
                utils.delete_hierarchy(self.new_root)
                self.new_root = None

            self.finish(context)

            bpy.ops.simplepaint.paint('INVOKE_DEFAULT')

            if self.placed_count > 0:
                return {'FINISHED'}

            return {'CANCELLED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            if self.new_root is not None:
                utils.delete_hierarchy(self.new_root)
                self.new_root = None

            self.finish(context)

            if self.placed_count > 0:
                return {'FINISHED'}

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
                context.scene.simplepaint_brush_size * 0.3
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

        source_root = utils.pick_item(
            self.source_collection
        )

        if source_root is None:
            return

        self.item_source_root = source_root
        self.item_random_quat = utils.roll_random_quat(context)
        self.item_scale_mult = utils.roll_scale_mult(context)

        self.new_root = utils.duplicate_item(
            context, source_root, self.placed_collection
        )

        self.new_root.matrix_world = utils.item_transform(
            context, source_root, location, normal,
            self.item_random_quat, self.item_scale_mult
        )

        self.state = 'DRAGGING'

    def finish(self, context):

        if self.draw_handler is not None:

            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handler, 'WINDOW'
            )

            self.draw_handler = None

        context.area.header_text_set(None)

    def cancel(self, context):

        self.finish(context)


# =========================================================
# FLOOD OPERATOR
# =========================================================

class SIMPLEPAINT_OT_flood(bpy.types.Operator):

    bl_idname = "simplepaint.flood"
    bl_label = "Flood"
    bl_options = {'REGISTER', 'UNDO'}

    bl_description = (
        "Cover the entire selected surface object(s) with items"
    )

    @classmethod
    def poll(cls, context):

        if context.scene.simplepaint_paint_mode != 'SURFACE':

            cls.poll_message_set(
                "Requires Paint On = 'Selected Surface(s)'"
            )

            return False

        return True

    def execute(self, context):

        source_collection = validate_prerequisites(self, context)

        if source_collection is None:
            return {'CANCELLED'}

        placed_collection = utils.get_placed_collection(context)

        targets = utils.get_surface_targets(
            context, source_collection, placed_collection
        )

        # Spacing is an absolute world distance, so flooding a whole
        # surface and painting a patch of it land items at the same
        # density. Brush Size is not involved here at all -- it only
        # scopes how much area a paint stroke covers.
        spacing = context.scene.simplepaint_spacing

        spatial_hash = utils.build_spatial_hash(
            placed_collection, spacing
        )

        total_placed = 0

        for obj in targets:

            total_placed += self.flood_object(
                context, obj, source_collection,
                placed_collection, spatial_hash, spacing
            )

        self.report(
            {'INFO'},
            f"Flooded {total_placed} item(s)"
        )

        return {'FINISHED'}

    def flood_object(
        self, context, obj, source_collection,
        placed_collection, spatial_hash, spacing
    ):

        triangles = utils.get_evaluated_triangles(context, obj)

        if not triangles:
            return 0

        samples = utils.sample_triangles(
            triangles, spacing, spatial_hash=spatial_hash
        )

        placed = 0

        for point, normal in samples:

            source_root = utils.pick_item(source_collection)

            if source_root is None:
                continue

            new_root = utils.duplicate_item(
                context, source_root, placed_collection
            )

            random_quat = utils.roll_random_quat(context)
            scale_mult = utils.roll_scale_mult(context)

            new_root.matrix_world = utils.item_transform(
                context, source_root, point, normal,
                random_quat, scale_mult
            )

            placed += 1

        return placed


classes = (
    SIMPLEPAINT_OT_paint,
    SIMPLEPAINT_OT_place_one,
    SIMPLEPAINT_OT_flood,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
