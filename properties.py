import bpy


def register():

    bpy.types.Scene.peoplelib_collection_name = (
        bpy.props.StringProperty(
            name="Collection",
            description=(
                "Name of the collection containing the "
                "source characters"
            ),
            default="PeopleLib"
        )
    )

    bpy.types.Scene.peoplelib_paint_mode = (
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

    bpy.types.Scene.peoplelib_surface = (
        bpy.props.PointerProperty(
            name="Base Mesh",
            description=(
                "Surface object to paint on when Paint On is "
                "'Selected Surface'"
            ),
            type=bpy.types.Object
        )
    )

    bpy.types.Scene.peoplelib_brush_size = (
        bpy.props.FloatProperty(
            name="Brush Size",
            description="Radius of the paint brush, in world units",
            default=1.0,
            min=0.01,
            soft_max=10.0,
            unit='LENGTH'
        )
    )

    bpy.types.Scene.peoplelib_density = (
        bpy.props.FloatProperty(
            name="Density",
            description=(
                "How tightly packed the stamped characters are "
                "within the brush"
            ),
            default=0.5,
            min=0.0,
            max=1.0,
            subtype='FACTOR'
        )
    )


def unregister():

    del bpy.types.Scene.peoplelib_collection_name
    del bpy.types.Scene.peoplelib_paint_mode
    del bpy.types.Scene.peoplelib_surface
    del bpy.types.Scene.peoplelib_brush_size
    del bpy.types.Scene.peoplelib_density
