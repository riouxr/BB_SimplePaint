import bpy


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
                    "Selected Surface",
                    "Only paint on the chosen base mesh"
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

    bpy.types.Scene.simplepaint_surface = (
        bpy.props.PointerProperty(
            name="Base Mesh",
            description=(
                "Surface object to paint on when Paint On is "
                "'Selected Surface'"
            ),
            type=bpy.types.Object
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

    bpy.types.Scene.simplepaint_density = (
        bpy.props.FloatProperty(
            name="Density",
            description=(
                "How tightly packed the stamped items are "
                "within the brush"
            ),
            default=0.5,
            min=0.0,
            max=1.0,
            subtype='FACTOR'
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
    del bpy.types.Scene.simplepaint_surface
    del bpy.types.Scene.simplepaint_brush_size
    del bpy.types.Scene.simplepaint_density
    del bpy.types.Scene.simplepaint_align_mode
    del bpy.types.Scene.simplepaint_random_rot_x
    del bpy.types.Scene.simplepaint_random_rot_y
    del bpy.types.Scene.simplepaint_random_rot_z
    del bpy.types.Scene.simplepaint_scale_min
    del bpy.types.Scene.simplepaint_scale_max
