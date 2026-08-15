import bpy
import gpu

from gpu_extras.batch import batch_for_shader

from . import utils


# Preview is a visual gauge, not the real placement pass, so it is
# capped well below what Flood would actually place on a huge surface.
MAX_PREVIEW_POINTS = 4000

DOT_COLOR = (0.25, 0.9, 1.0, 0.9)
DOT_SIZE = 4.0


_draw_handle = None

# cache_key -> what the samples were generated for
# entries: obj_name -> (sample_matrix, [(point, normal), ...])
_cache_key = None
_cache_entries = {}


def clear_cache():

    global _cache_key, _cache_entries

    _cache_key = None
    _cache_entries = {}


def tag_redraw_all(context):

    if context is None or context.screen is None:
        return

    for area in context.screen.areas:

        if area.type == 'VIEW_3D':
            area.tag_redraw()


def get_preview_targets(context):

    source_collection = utils.get_source_collection(context)

    # Deliberately does NOT use get_placed_collection(): that creates
    # the collection if missing, and creating data inside a draw
    # handler is not safe.
    placed_collection = bpy.data.collections.get(
        utils.PLACED_COLLECTION_NAME
    )

    return utils.get_surface_targets(
        context, source_collection, placed_collection
    )


def build_cache_key(context, targets):

    scene = context.scene

    # Scale is part of the key because scaling an object genuinely
    # changes how many items fit on it. Location/rotation are not:
    # those are rigid, so cached samples are just re-transformed on
    # draw instead of being resampled.
    return (
        round(scene.simplepaint_spacing, 6),
        tuple(
            (
                obj.name,
                tuple(
                    round(v, 5)
                    for v in obj.matrix_world.to_scale()
                ),
            )
            for obj in targets
        ),
    )


def rebuild_cache(context, targets):

    global _cache_entries

    _cache_entries = {}

    spacing = context.scene.simplepaint_spacing

    budget = MAX_PREVIEW_POINTS

    for obj in targets:

        if budget <= 0:
            break

        triangles = utils.get_evaluated_triangles(context, obj)

        if not triangles:
            continue

        samples = utils.sample_triangles(
            triangles, spacing, max_points=budget
        )

        if not samples:
            continue

        budget -= len(samples)

        _cache_entries[obj.name] = (
            obj.matrix_world.copy(),
            samples,
        )


def get_draw_coords(context):

    global _cache_key

    targets = get_preview_targets(context)

    if not targets:
        return []

    key = build_cache_key(context, targets)

    if key != _cache_key:

        rebuild_cache(context, targets)
        _cache_key = key

    coords = []

    spacing = context.scene.simplepaint_spacing
    offset = max(spacing * 0.02, 0.001)

    for obj in targets:

        entry = _cache_entries.get(obj.name)

        if entry is None:
            continue

        sample_matrix, samples = entry

        # Rigid delta since sampling: lets the dots follow the object
        # as it is moved or rotated without resampling the surface.
        try:
            delta = obj.matrix_world @ sample_matrix.inverted()
        except ValueError:
            continue

        delta_rot = delta.to_3x3()

        for point, normal in samples:

            world_point = delta @ point
            world_normal = delta_rot @ normal

            coords.append(
                world_point + world_normal * offset
            )

    return coords


def draw_callback():

    context = bpy.context
    scene = context.scene

    if not getattr(scene, "simplepaint_show_preview", False):
        return

    if scene.simplepaint_paint_mode != 'SURFACE':
        return

    coords = get_draw_coords(context)

    if not coords:
        return

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.point_size_set(DOT_SIZE)

    shader.bind()
    shader.uniform_float("color", DOT_COLOR)
    batch.draw(shader)

    gpu.state.point_size_set(1.0)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def on_depsgraph_update(scene, depsgraph):

    # Only geometry edits need a resample; transforms are handled by
    # the rigid-delta path in get_draw_coords().
    if _cache_key is None:
        return

    for update in depsgraph.updates:

        if not update.is_updated_geometry:
            continue

        obj_id = update.id

        if getattr(obj_id, "name", None) in _cache_entries:

            clear_cache()
            return


def register():

    global _draw_handle

    if _draw_handle is None:

        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback, (), 'WINDOW', 'POST_VIEW'
        )

    if on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(
            on_depsgraph_update
        )


def unregister():

    global _draw_handle

    if on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(
            on_depsgraph_update
        )

    if _draw_handle is not None:

        bpy.types.SpaceView3D.draw_handler_remove(
            _draw_handle, 'WINDOW'
        )

        _draw_handle = None

    clear_cache()
