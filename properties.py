import bpy
import math

from . import preview


def refresh_preview(self, context):

    preview.clear_cache()
    preview.tag_redraw_all(context)


def redraw_only(self, context):

    preview.tag_redraw_all(context)


AXES = ('x', 'y', 'z')

ROT_LABELS = {'x': "X", 'y': "Y", 'z': "Z"}


def register():

    bpy.types.Scene.simplepaint_collection = (
        bpy.props.PointerProperty(
            name="Collection",
            description=(
                "Collection holding the source items to paint"
            ),
            type=bpy.types.Collection
        )
    )

    bpy.types.Scene.simplepaint_paint_mode = (
        bpy.props.EnumProperty(
            name="Paint On",
            description="What the brush is allowed to hit",
            items=(
                (
                    'SURFACE',
                    "Selected Surface(s)",
                    "Only paint on the currently selected "
                    "mesh object(s)"
                ),
                (
                    'SCENE',
                    "Any Surface",
                    "Paint on any surface under the cursor"
                ),
            ),
            default='SURFACE',
            update=refresh_preview
        )
    )

    bpy.types.Scene.simplepaint_brush_size = (
        bpy.props.FloatProperty(
            name="Brush Size",
            description=(
                "How large an area a paint stroke covers, in world "
                "units. This does not affect density -- Spacing "
                "alone controls that"
            ),
            default=1.0,
            min=0.01,
            soft_max=10.0,
            unit='LENGTH'
        )
    )

    bpy.types.Scene.simplepaint_spacing = (
        bpy.props.FloatProperty(
            name="Spacing",
            description=(
                "Minimum distance between placed items, in world "
                "units. Because this is a real world-space "
                "distance, Paint and Flood produce the same "
                "coverage density"
            ),
            default=1.0,
            min=0.001,
            soft_max=20.0,
            unit='LENGTH',
            update=refresh_preview
        )
    )

    bpy.types.Scene.simplepaint_show_preview = (
        bpy.props.BoolProperty(
            name="Preview Spacing",
            description=(
                "Show a dot on each selected surface where an "
                "item would land at the current Spacing"
            ),
            default=False,
            update=refresh_preview
        )
    )

    bpy.types.Scene.simplepaint_preview_dot_size = (
        bpy.props.IntProperty(
            name="Dot Size",
            description=(
                "On-screen size of the preview dots, in pixels"
            ),
            default=8,
            min=1,
            max=32,
            update=redraw_only
        )
    )

    # -----------------------------------------------------
    # ALIGN
    # -----------------------------------------------------

    bpy.types.Scene.simplepaint_align_mode = (
        bpy.props.EnumProperty(
            name="Align",
            description=(
                "How placed items are oriented relative to the "
                "surface they land on"
            ),
            items=(
                (
                    'SURFACE',
                    "Surface",
                    "Tilt to match the surface normal under "
                    "the item"
                ),
                (
                    'X',
                    "X",
                    "Always keep the item's up axis pointing "
                    "along world X, regardless of surface tilt"
                ),
                (
                    'Y',
                    "Y",
                    "Always keep the item's up axis pointing "
                    "along world Y, regardless of surface tilt"
                ),
                (
                    'Z',
                    "Z",
                    "Always keep the item's up axis pointing "
                    "along world Z, regardless of surface tilt"
                ),
                (
                    'OBJECT',
                    "Object",
                    "Point a chosen local axis of the item at "
                    "a target object"
                ),
            ),
            default='Z'
        )
    )

    bpy.types.Scene.simplepaint_orient_target = (
        bpy.props.PointerProperty(
            name="Orient Target",
            description=(
                "Object that placed items point their chosen "
                "axis toward, when Align is 'Object'"
            ),
            type=bpy.types.Object
        )
    )

    bpy.types.Scene.simplepaint_orient_axis = (
        bpy.props.EnumProperty(
            name="Orient Axis",
            description=(
                "Which local axis of the item points at the "
                "Orient Target"
            ),
            items=(
                ('X', "X", "Local +X axis"),
                ('Y', "Y", "Local +Y axis"),
                ('Z', "Z", "Local +Z axis"),
                ('-X', "-X", "Local -X axis"),
                ('-Y', "-Y", "Local -Y axis"),
                ('-Z', "-Z", "Local -Z axis"),
            ),
            default='Z'
        )
    )

    # -----------------------------------------------------
    # RANDOM ROTATION (per axis, min/max)
    # -----------------------------------------------------

    bpy.types.Scene.simplepaint_rot_sync = (
        bpy.props.BoolProperty(
            name="Sync",
            description=(
                "Use one Min/Max range for every enabled "
                "rotation axis"
            ),
            default=True
        )
    )

    for axis in AXES:

        setattr(
            bpy.types.Scene,
            f"simplepaint_random_rot_{axis}",
            bpy.props.BoolProperty(
                name=ROT_LABELS[axis],
                description=(
                    "Randomize rotation around the local "
                    f"{ROT_LABELS[axis]} axis"
                ),
                default=False
            )
        )

        setattr(
            bpy.types.Scene,
            f"simplepaint_rot_min_{axis}",
            bpy.props.FloatProperty(
                name="Min",
                description=(
                    "Minimum random rotation around the local "
                    f"{ROT_LABELS[axis]} axis"
                ),
                default=0.0,
                subtype='ANGLE',
                unit='ROTATION'
            )
        )

        setattr(
            bpy.types.Scene,
            f"simplepaint_rot_max_{axis}",
            bpy.props.FloatProperty(
                name="Max",
                description=(
                    "Maximum random rotation around the local "
                    f"{ROT_LABELS[axis]} axis"
                ),
                default=math.radians(360.0),
                subtype='ANGLE',
                unit='ROTATION'
            )
        )

    # -----------------------------------------------------
    # RANDOM SCALE (per axis, min/max)
    # -----------------------------------------------------

    bpy.types.Scene.simplepaint_scale_sync = (
        bpy.props.BoolProperty(
            name="Sync",
            description=(
                "Scale every axis by the same random factor, "
                "keeping items proportional"
            ),
            default=True
        )
    )

    for axis in AXES:

        setattr(
            bpy.types.Scene,
            f"simplepaint_scale_min_{axis}",
            bpy.props.FloatProperty(
                name="Min",
                description=(
                    "Minimum random scale factor on the "
                    f"{ROT_LABELS[axis]} axis"
                ),
                default=1.0,
                min=0.001,
                soft_max=10.0
            )
        )

        setattr(
            bpy.types.Scene,
            f"simplepaint_scale_max_{axis}",
            bpy.props.FloatProperty(
                name="Max",
                description=(
                    "Maximum random scale factor on the "
                    f"{ROT_LABELS[axis]} axis"
                ),
                default=1.0,
                min=0.001,
                soft_max=10.0
            )
        )


def unregister():

    del bpy.types.Scene.simplepaint_collection
    del bpy.types.Scene.simplepaint_paint_mode
    del bpy.types.Scene.simplepaint_brush_size
    del bpy.types.Scene.simplepaint_spacing
    del bpy.types.Scene.simplepaint_show_preview
    del bpy.types.Scene.simplepaint_preview_dot_size
    del bpy.types.Scene.simplepaint_align_mode
    del bpy.types.Scene.simplepaint_orient_target
    del bpy.types.Scene.simplepaint_orient_axis
    del bpy.types.Scene.simplepaint_rot_sync
    del bpy.types.Scene.simplepaint_scale_sync

    for axis in AXES:

        delattr(
            bpy.types.Scene, f"simplepaint_random_rot_{axis}"
        )
        delattr(bpy.types.Scene, f"simplepaint_rot_min_{axis}")
        delattr(bpy.types.Scene, f"simplepaint_rot_max_{axis}")
        delattr(bpy.types.Scene, f"simplepaint_scale_min_{axis}")
        delattr(bpy.types.Scene, f"simplepaint_scale_max_{axis}")
