import bisect
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

    return context.scene.simplepaint_collection


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


def get_surface_targets(context, source_collection, placed_collection):

    return [
        obj
        for obj in context.selected_objects
        if obj.type == 'MESH'
        and not is_library_object(
            obj, source_collection, placed_collection
        )
    ]


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

def remap_pointer_props(owner, id_map):

    for prop in owner.bl_rna.properties:

        if prop.type != 'POINTER':
            continue

        if prop.fixed_type.identifier != 'Object':
            continue

        if prop.is_readonly:
            continue

        replacement = id_map.get(
            getattr(owner, prop.identifier, None)
        )

        if replacement is not None:
            setattr(owner, prop.identifier, replacement)


def remap_constraint(constraint, id_map):

    remap_pointer_props(constraint, id_map)

    for sub_target in getattr(constraint, "targets", []):
        remap_pointer_props(sub_target, id_map)


def remap_object_references(new_obj, id_map):

    """Point copied modifiers and constraints at the copied hierarchy.

    obj.copy() keeps the originals' pointers, so without this an
    Armature modifier on a painted character still deforms from the
    source rig and its own bones do nothing.
    """

    for modifier in new_obj.modifiers:
        remap_pointer_props(modifier, id_map)

    for constraint in new_obj.constraints:
        remap_constraint(constraint, id_map)

    if new_obj.pose is not None:

        for pose_bone in new_obj.pose.bones:

            for constraint in pose_bone.constraints:
                remap_constraint(constraint, id_map)


def duplicate_item(context, source_root, placed_collection):

    hierarchy = [source_root] + list(
        source_root.children_recursive
    )

    id_map = {}

    for obj in hierarchy:

        new_obj = obj.copy()

        placed_collection.objects.link(new_obj)

        id_map[obj] = new_obj

    for original, new_obj in id_map.items():

        if original.parent is not None and original.parent in id_map:

            new_obj.parent = id_map[original.parent]
            new_obj.matrix_parent_inverse = (
                original.matrix_parent_inverse.copy()
            )

        remap_object_references(new_obj, id_map)

    return id_map[source_root]


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


def raycast_targets(context, mouse_coord, target_objects):

    region = context.region
    rv3d = context.region_data

    if region is None or rv3d is None:
        return None

    ray_origin = view3d_utils.region_2d_to_origin_3d(
        region, rv3d, mouse_coord
    )

    best_hit = None
    best_dist = None

    for target_object in target_objects:

        hit = raycast(
            context, mouse_coord, target_object=target_object
        )

        if hit is None:
            continue

        dist = (hit[0] - ray_origin).length

        if best_dist is None or dist < best_dist:
            best_hit = hit
            best_dist = dist

    return best_hit


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
    '-X': Vector((-1.0, 0.0, 0.0)),
    '-Y': Vector((0.0, -1.0, 0.0)),
    '-Z': Vector((0.0, 0.0, -1.0)),
}


def get_target_up(align_mode, hit_normal):

    if align_mode == 'SURFACE':
        return hit_normal.normalized()

    return AXIS_VECTORS.get(align_mode, AXIS_VECTORS['Z']).copy()


def compute_align_quat(source_root, target_up, source_axis=None):

    if source_axis is None:
        source_axis = Vector((0.0, 0.0, 1.0))

    source_matrix = source_root.matrix_world.to_3x3()
    source_dir = (source_matrix @ source_axis)

    if source_dir.length_squared < 1e-12:
        source_dir = Vector((0.0, 0.0, 1.0))
    else:
        source_dir.normalize()

    target_up = target_up.normalized()

    delta = source_dir.rotation_difference(target_up)
    source_quat = source_root.matrix_world.to_quaternion()

    return delta @ source_quat


def random_in_range(low, high):

    return random.uniform(min(low, high), max(low, high))


def build_matrix(location, rotation_quat, scale_vec):

    return Matrix.LocRotScale(location, rotation_quat, scale_vec)


def item_transform(context, source_root, location, hit_normal, random_quat, scale_mult):

    scene = context.scene
    align_mode = scene.simplepaint_align_mode

    if align_mode == 'OBJECT':

        target_object = scene.simplepaint_orient_target
        source_axis = AXIS_VECTORS.get(
            scene.simplepaint_orient_axis, AXIS_VECTORS['Z']
        )

        if target_object is not None:

            target_up = target_object.matrix_world.translation - location

            if target_up.length_squared < 1e-12:
                target_up = Vector((0.0, 0.0, 1.0))
            else:
                target_up.normalize()

        else:
            target_up = Vector((0.0, 0.0, 1.0))

    else:

        target_up = get_target_up(align_mode, hit_normal)
        source_axis = Vector((0.0, 0.0, 1.0))

    align_quat = compute_align_quat(source_root, target_up, source_axis)

    final_quat = align_quat @ random_quat

    base = source_root.scale

    scale_vec = Vector((
        base.x * scale_mult.x,
        base.y * scale_mult.y,
        base.z * scale_mult.z,
    ))

    return build_matrix(location, final_quat, scale_vec)


def roll_random_quat(context):

    scene = context.scene
    sync = scene.simplepaint_rot_sync

    quat = Quaternion()

    for axis in ('x', 'y', 'z'):

        if not getattr(scene, f"simplepaint_random_rot_{axis}"):
            continue

        # When synced, every enabled axis draws from the X range so
        # there is a single Min/Max pair to think about.
        source = 'x' if sync else axis

        angle = random_in_range(
            getattr(scene, f"simplepaint_rot_min_{source}"),
            getattr(scene, f"simplepaint_rot_max_{source}"),
        )

        quat = quat @ Quaternion(
            AXIS_VECTORS[axis.upper()], angle
        )

    return quat


def roll_scale_mult(context):

    scene = context.scene

    axes = ('x', 'y', 'z')

    enabled = [
        axis
        for axis in axes
        if getattr(scene, f"simplepaint_random_scale_{axis}")
    ]

    # Disabled axes keep a multiplier of 1.0, so scaling only X and Y
    # leaves Z at the source object's own scale.
    mult = [1.0, 1.0, 1.0]

    if not enabled:
        return Vector(mult)

    if scene.simplepaint_scale_sync:

        # One factor shared by the enabled axes, so they stay
        # proportional to each other.
        factor = random_in_range(
            scene.simplepaint_scale_min_x,
            scene.simplepaint_scale_max_x,
        )

        for index, axis in enumerate(axes):

            if axis in enabled:
                mult[index] = factor

        return Vector(mult)

    for index, axis in enumerate(axes):

        if axis not in enabled:
            continue

        mult[index] = random_in_range(
            getattr(scene, f"simplepaint_scale_min_{axis}"),
            getattr(scene, f"simplepaint_scale_max_{axis}"),
        )

    return Vector(mult)


# =========================================================
# MESH SURFACE SAMPLING (flood fill)
# =========================================================

def triangle_area(verts):

    return (
        (verts[1] - verts[0]).cross(verts[2] - verts[0]).length
        * 0.5
    )


def sample_point_in_triangle(verts):

    r1 = random.random()
    r2 = random.random()

    sqrt_r1 = math.sqrt(r1)

    a = 1.0 - sqrt_r1
    b = sqrt_r1 * (1.0 - r2)
    c = sqrt_r1 * r2

    return verts[0] * a + verts[1] * b + verts[2] * c


def get_evaluated_triangles(context, obj):

    depsgraph = context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)

    mesh = obj_eval.to_mesh()
    mesh.calc_loop_triangles()

    matrix = obj_eval.matrix_world
    normal_matrix = matrix.to_3x3()

    triangles = []

    for tri in mesh.loop_triangles:

        verts = [
            matrix @ mesh.vertices[i].co
            for i in tri.vertices
        ]

        area = triangle_area(verts)

        if area <= 1e-10:
            continue

        normal = (normal_matrix @ tri.normal).normalized()

        triangles.append((verts, normal, area))

    obj_eval.to_mesh_clear()

    return triangles


class WeightedTriangles:

    def __init__(self, triangles):

        self.triangles = triangles

        self.cumulative = []
        running = 0.0

        for verts, normal, area in triangles:
            running += area
            self.cumulative.append(running)

        self.total_area = running

    def pick(self):

        if not self.triangles:
            return None

        r = random.uniform(0.0, self.total_area)
        idx = bisect.bisect_left(self.cumulative, r)
        idx = min(idx, len(self.triangles) - 1)

        return self.triangles[idx]


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


# Dart-throwing with a hard minimum distance saturates well below
# the theoretical area / spacing^2 packing, so aiming for that count
# just burns the whole attempt budget on rejections. This is the
# realistic share of it to target.
PACKING_EFFICIENCY = 0.6

ATTEMPTS_PER_TARGET = 20


def sample_triangles(
    triangles, spacing, max_points=None, spatial_hash=None
):

    if not triangles or spacing <= 0.0:
        return []

    total_area = sum(area for _, _, area in triangles)

    if total_area <= 0.0:
        return []

    weighted = WeightedTriangles(triangles)

    if spatial_hash is None:
        spatial_hash = SpatialHash(spacing)

    target_count = max(
        1,
        int(
            total_area / (spacing * spacing) * PACKING_EFFICIENCY
        )
    )

    if max_points is not None:
        target_count = min(target_count, max_points)

    if target_count <= 0:
        return []

    samples = []

    for _ in range(target_count * ATTEMPTS_PER_TARGET):

        if len(samples) >= target_count:
            break

        triangle = weighted.pick()

        if triangle is None:
            break

        verts, normal, area = triangle

        point = sample_point_in_triangle(verts)

        if spatial_hash.is_too_close(point, spacing):
            continue

        spatial_hash.add(point)

        samples.append((point, normal))

    return samples
