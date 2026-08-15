import bpy

from . import preview


def refresh_preview(self, context):

    preview.clear_cache()
    preview.tag_redraw_all(context)


def register():

    bpy.types.Scene.simplepaint_collection_name = (
        bpy.props.StringProperty(
            name="Collection",
            description=(
                "Name of the collection containing the "
                "source items"
            ),
            default="PaintItems"
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
            default='SURFACE'
        )
    )

    bpy.types.Scene.simplepaint_brush_size = (
        bpy.props.FloatProperty(
            name="Brush Size",
            description="Radius of the paint brush, in world units",
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

    bpy.types.Scene.simplepaint_random_rot_x = (
        bpy.props.BoolProperty(
            name="X",
            description="Randomize rotation around the local X axis",
            default=False
        )
    )

    bpy.types.Scene.simplepaint_random_rot_y = (
        bpy.props.BoolProperty(
            name="Y",
            description="Randomize rotation around the local Y axis",
            default=False
        )
    )

    bpy.types.Scene.simplepaint_random_rot_z = (
        bpy.props.BoolProperty(
            name="Z",
            description="Randomize rotation around the local Z axis",
            default=False
        )
    )

    bpy.types.Scene.simplepaint_scale_min = (
        bpy.props.FloatProperty(
            name="Min",
            description="Minimum random uniform scale factor",
            default=1.0,
            min=0.001,
            soft_max=10.0
        )
    )

    bpy.types.Scene.simplepaint_scale_max = (
        bpy.props.FloatProperty(
            name="Max",
            description="Maximum random uniform scale factor",
            default=1.0,
            min=0.001,
            soft_max=10.0
        )
    )


def unregister():

    del bpy.types.Scene.simplepaint_collection_name
    del bpy.types.Scene.simplepaint_paint_mode
    del bpy.types.Scene.simplepaint_brush_size
    del bpy.types.Scene.simplepaint_spacing
    del bpy.types.Scene.simplepaint_show_preview
    del bpy.types.Scene.simplepaint_align_mode
    del bpy.types.Scene.simplepaint_orient_target
    del bpy.types.Scene.simplepaint_orient_axis
    del bpy.types.Scene.simplepaint_random_rot_x
    del bpy.types.Scene.simplepaint_random_rot_y
    del bpy.types.Scene.simplepaint_random_rot_z
    del bpy.types.Scene.simplepaint_scale_min
    del bpy.types.Scene.simplepaint_scale_max
