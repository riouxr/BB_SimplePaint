import bpy

from . import utils


class SIMPLEPAINT_PT_panel(bpy.types.Panel):

    bl_label = "Simple Paint"
    bl_idname = "SIMPLEPAINT_PT_panel"

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
            "simplepaint_collection_name",
            text="Collection"
        )

        if source_collection is None:

            box.label(
                text="Collection not found",
                icon='ERROR'
            )

        else:

            count = len(
                utils.get_item_roots(source_collection)
            )

            box.label(
                text=f"{count} item(s)",
                icon='MESH_DATA'
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
            "simplepaint_paint_mode",
            text=""
        )

        if scene.simplepaint_paint_mode == 'SURFACE':

            targets = utils.get_surface_targets(
                context,
                source_collection,
                utils.get_placed_collection(context)
            )

            if targets:

                names = ", ".join(
                    obj.name for obj in targets[:3]
                )

                if len(targets) > 3:
                    names += f" (+{len(targets) - 3})"

                box.label(
                    text=f"Selected: {names}",
                    icon='RESTRICT_SELECT_OFF'
                )

            else:

                box.label(
                    text="Select mesh object(s) as surface",
                    icon='ERROR'
                )

        # -------------------------------------------------
        # ALIGN / ROTATION / SCALE
        # -------------------------------------------------

        layout.separator()

        box = layout.box()

        box.label(
            text="Orientation and Scale",
            icon='ORIENTATION_NORMAL'
        )

        box.prop(
            scene,
            "simplepaint_align_mode",
            text="Align"
        )

        if scene.simplepaint_align_mode == 'OBJECT':

            box.prop(
                scene,
                "simplepaint_orient_target",
                text="Target"
            )

            box.prop(
                scene,
                "simplepaint_orient_axis",
                text="Axis"
            )

        row = box.row(align=True)

        row.label(text="Random Rotation:")
        row.prop(
            scene, "simplepaint_random_rot_x",
            text="X", toggle=True
        )
        row.prop(
            scene, "simplepaint_random_rot_y",
            text="Y", toggle=True
        )
        row.prop(
            scene, "simplepaint_random_rot_z",
            text="Z", toggle=True
        )

        row = box.row(align=True)

        row.label(text="Random Scale:")
        row.prop(
            scene, "simplepaint_scale_min", text="Min"
        )
        row.prop(
            scene, "simplepaint_scale_max", text="Max"
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
            "simplepaint_brush_size",
            text="Size"
        )

        box.prop(
            scene,
            "simplepaint_density",
            text="Density"
        )

        row = box.row(align=True)

        paint_op = row.operator(
            "simplepaint.paint",
            text="Paint",
            icon='BRUSH_DATA'
        )

        paint_op.erase = False

        erase_op = row.operator(
            "simplepaint.paint",
            text="Erase",
            icon='TRASH'
        )

        erase_op.erase = True

        row = box.row(align=True)

        row.enabled = scene.simplepaint_paint_mode == 'SURFACE'

        row.operator(
            "simplepaint.flood",
            text="Flood",
            icon='OUTLINER_OB_POINTCLOUD'
        )

        if scene.simplepaint_paint_mode != 'SURFACE':

            box.label(
                text="Flood needs 'Selected Surface(s)'",
                icon='INFO'
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
            "simplepaint.place_one",
            text="Place One"
        )


classes = (
    SIMPLEPAINT_PT_panel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
