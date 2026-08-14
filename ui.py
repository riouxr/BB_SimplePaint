import bpy

from . import utils


class PEOPLELIB_PT_panel(bpy.types.Panel):

    bl_label = "People Lib"
    bl_idname = "PEOPLELIB_PT_panel"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        source_collection = utils.get_source_collection(
            context
        )

        # -------------------------------------------------
        # SOURCE COLLECTION
        # -------------------------------------------------

        box = layout.box()

        row = box.row()

        row.prop(
            scene,
            "peoplelib_collection_name",
            text="Collection"
        )

        if source_collection is None:

            box.label(
                text="Collection not found",
                icon='ERROR'
            )

        else:

            count = len(
                utils.get_character_roots(source_collection)
            )

            box.label(
                text=f"{count} character(s)",
                icon='COMMUNITY'
            )

        # -------------------------------------------------
        # PAINT ON
        # -------------------------------------------------

        layout.separator()

        box = layout.box()

        box.label(
            text="Paint On",
            icon='SNAP_FACE'
        )

        box.prop(
            scene,
            "peoplelib_paint_mode",
            text=""
        )

        if scene.peoplelib_paint_mode == 'SURFACE':

            box.prop(
                scene,
                "peoplelib_surface",
                text="Base Mesh"
            )

        # -------------------------------------------------
        # BRUSH
        # -------------------------------------------------

        layout.separator()

        box = layout.box()

        box.label(
            text="Brush",
            icon='BRUSH_DATA'
        )

        box.prop(
            scene,
            "peoplelib_brush_size",
            text="Size"
        )

        box.prop(
            scene,
            "peoplelib_density",
            text="Density"
        )

        box.operator(
            "peoplelib.paint",
            text="Paint",
            icon='BRUSH_DATA'
        )

        # -------------------------------------------------
        # PLACE ONE
        # -------------------------------------------------

        layout.separator()

        box = layout.box()

        box.label(
            text="Place One",
            icon='OBJECT_ORIGIN'
        )

        box.operator(
            "peoplelib.place_one",
            text="Place One Character"
        )


classes = (
    PEOPLELIB_PT_panel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
