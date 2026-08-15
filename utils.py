import bpy
import math
import random

from mathutils import Vector, Matrix, Quaternion
from bpy_extras import view3d_utils


PLACED_COLLECTION_NAME = "SimplePaint_Placed"

ANTI_REPEAT_HISTORY = 20

_pick_history = []


# =========================================================
# COLLECTIONS
# =========================================================

def get_source_collection(context):

    name = context.scene.simplepaint_collection_name

    return bpy.data.collections.get(name)


def get_placed_collection(context):

    collection = bpy.data.collections.get(
        PLACED_COLLECTION_NAME
    )

    if collection is None:

        collection = bpy.data.collections.new(
            PLACED_COLLECTION_NAME
        )

        context.scene.collection.children.link(
            collection
        )

    return collection


def is_library_object(obj, source_collection, placed_collection):

    if source_collection is not None:

        if obj.name in source_collection.objects:
            return True

    if placed_collection is not None:

        if obj.name in placed_collection.objects:
            return True

    return False


# =========================================================
# ITEM PICKER (anti-repeat)
# =========================================================

def reset_pick_history():

    _pick_history.clear()


def get_item_roots(source_collection):

    return [
        obj
        for obj in source_collection.objects
        if obj.parent is None
    ]


def pick_item(source_collection):

    members = get_item_roots(source_collection)

    if not members:
        return None

    avoid_count = min(
        ANTI_REPEAT_HISTORY,
        max(0, len(members) - 1)
    )

    recent = (
        _pick_history[-avoid_count:]
        if avoid_count
        else []
    )

    candidates = [
        obj
        for obj in members
        if obj not in recent
    ]

    if not candidates:
        candidates = members

    choice = random.choice(candidates)

    _pick_history.append(choice)

    if len(_pick_history) > ANTI_REPEAT_HISTORY:
        del _pick_history[0]

    return choice


# =========================================================
# HIERARCHY DUPLICATION (linked duplicate)
# =========================================================

def duplicate_item(context, source_root, placed_collection):

    hierarchy = [source_root] + list(
        source_root.children_recursive
    )

    for obj in context.view_layer.objects:
        obj.select_set(False)

    for obj in hierarchy:
        obj.select_set(True)

    context.view_layer.objects.active = source_root

    bpy.ops.object.duplicate(linked=True)

    new_root = context.view_layer.objects.active

    new_objects = list(context.selected_objects)

    for obj in new_objects:

        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)

        placed_collection.objects.link(obj)

    return new_root


def delete_hierarchy(root):

    if root is None:
        return

    objects = [root] + list(root.children_recursive)

    for obj in objects:

        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass


# =========================================================
# RAYCASTING
# =========================================================

def raycast(context, mouse_coord, target_object=None, exclude=None):

    region = context.region
    rv3d = context.region_data

    if region is None or rv3d is None:
        return None

    view_vector = view3d_utils.region_2d_to_vector_3d(
        region, rv3d, mouse_coord
    )

    ray_origin = view3d_utils.region_2d_to_origin_3d(
        region, rv3d, mouse_coord
    )

    depsgraph = context.evaluated_depsgraph_get()

    if target_object is not None:

        obj_eval = target_object.evaluated_get(depsgraph)

        matrix = obj_eval.matrix_world
        matrix_inv = matrix.inverted()

        ray_origin_obj = matrix_inv @ ray_origin

        ray_target_obj = matrix_inv @ (
            ray_origin + view_vector
        )

        ray_dir_obj = (
            ray_target_obj - ray_origin_obj
        ).normalized()

        success, location, normal, index = obj_eval.ray_cast(
            ray_origin_obj, ray_dir_obj
        )

        if not success:
            return None

        world_location = matrix @ location
        world_normal = (
            matrix.to_3x3() @ normal
        ).normalized()

        return world_location, world_normal, target_object

    success, location, normal, index, hit_obj, matrix = (
        context.scene.ray_cast(
            depsgraph, ray_origin, view_vector
        )
    )

    if not success:
        return None

    if exclude is not None and exclude(hit_obj):
        return None

    return location, normal, hit_obj


def location_to_screen(context, world_point):

    region = context.region
    rv3d = context.region_data

    if region is None or rv3d is None:
        return None

    return view3d_utils.location_3d_to_region_2d(
        region, rv3d, world_point
    )


def world_radius_to_pixels(context, world_point, world_radius):

    region = context.region
    rv3d = context.region_data

    if region is None or rv3d is None:
        return 60.0

    right = rv3d.view_rotation @ Vector(
        (1.0, 0.0, 0.0)
    )

    p1 = view3d_utils.location_3d_to_region_2d(
        region, rv3d, world_point
    )

    p2 = view3d_utils.location_3d_to_region_2d(
        region, rv3d, world_point + right * world_radius
    )

    if p1 is None or p2 is None:
        return 60.0

    return (p2 - p1).length


def random_point_in_disk(radius):

    r = radius * math.sqrt(random.random())
    theta = random.uniform(0.0, 2.0 * math.pi)

    return r * math.cos(theta), r * math.sin(theta)


# =========================================================
# ALIGNMENT / ROTATION / SCALE
# =========================================================

AXIS_VECTORS = {
    'X': Vector((1.0, 0.0, 0.0)),
    'Y': Vector((0.0, 1.0, 0.0)),
    'Z': Vector((0.0, 0.0, 1.0)),
}


def get_target_up(align_mode, hit_normal):

    if align_mode == 'SURFACE':
        return hit_normal.normalized()

    return AXIS_VECTORS.get(align_mode, AXIS_VECTORS['Z']).copy()


def compute_align_quat(source_root, target_up):

    source_matrix = source_root.matrix_world.to_3x3()
    source_up = (source_matrix @ Vector((0.0, 0.0, 1.0)))

    if source_up.length_squared < 1e-12:
        source_up = Vector((0.0, 0.0, 1.0))
    else:
        source_up.normalize()

    target_up = target_up.normalized()

    delta = source_up.rotation_difference(target_up)
    source_quat = source_root.matrix_world.to_quaternion()

    return delta @ source_quat


def random_axis_quat(random_x, random_y, random_z):

    quat = Quaternion()

    if random_x:
        quat = quat @ Quaternion(
            AXIS_VECTORS['X'], random.uniform(0.0, 2.0 * math.pi)
        )

    if random_y:
        quat = quat @ Quaternion(
            AXIS_VECTORS['Y'], random.uniform(0.0, 2.0 * math.pi)
        )

    if random_z:
        quat = quat @ Quaternion(
            AXIS_VECTORS['Z'], random.uniform(0.0, 2.0 * math.pi)
        )

    return quat


def random_scale_factor(scale_min, scale_max):

    lo = min(scale_min, scale_max)
    hi = max(scale_min, scale_max)

    return random.uniform(lo, hi)


def build_matrix(location, rotation_quat, scale_vec):

    return Matrix.LocRotScale(location, rotation_quat, scale_vec)


def item_transform(context, source_root, location, hit_normal, random_quat, scale_factor):

    align_mode = context.scene.simplepaint_align_mode

    target_up = get_target_up(align_mode, hit_normal)

    align_quat = compute_align_quat(source_root, target_up)

    final_quat = align_quat @ random_quat

    scale_vec = Vector(source_root.scale) * scale_factor

    return build_matrix(location, final_quat, scale_vec)


def roll_random_quat(context):

    scene = context.scene

    return random_axis_quat(
        scene.simplepaint_random_rot_x,
        scene.simplepaint_random_rot_y,
        scene.simplepaint_random_rot_z,
    )


def roll_scale_factor(context):

    scene = context.scene

    return random_scale_factor(
        scene.simplepaint_scale_min,
        scene.simplepaint_scale_max,
    )


# =========================================================
# SPATIAL HASH (overlap avoidance)
# =========================================================

class SpatialHash:

    def __init__(self, cell_size):

        self.cell_size = max(cell_size, 0.001)
        self.cells = {}

    def _key(self, pos):

        return (
            math.floor(pos.x / self.cell_size),
            math.floor(pos.y / self.cell_size),
            math.floor(pos.z / self.cell_size),
        )

    def add(self, pos):

        key = self._key(pos)

        self.cells.setdefault(key, []).append(
            pos.copy()
        )

    def is_too_close(self, pos, min_dist):

        if min_dist <= 0.0:
            return False

        key = self._key(pos)
        min_dist_sq = min_dist * min_dist

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):

                    neighbor = (
                        key[0] + dx,
                        key[1] + dy,
                        key[2] + dz,
                    )

                    for other in self.cells.get(neighbor, []):

                        if (other - pos).length_squared < min_dist_sq:
                            return True

        return False


def build_spatial_hash(placed_collection, cell_size):

    spatial_hash = SpatialHash(cell_size)

    for obj in placed_collection.objects:

        if obj.parent is not None:
            continue

        spatial_hash.add(obj.matrix_world.translation)

    return spatial_hash


def density_to_spacing(brush_size, density):

    spacing = brush_size * (1.05 - density) * 0.5

    return max(spacing, 0.05)
