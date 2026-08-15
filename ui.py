import bpy

from . import utils


AXES = ('x', 'y', 'z')

AXIS_LABELS = {'x': "X", 'y': "Y", 'z': "Z"}


class SIMPLEPAINT_PT_panel(bpy.types.Panel):

    bl_label = "BB Simple Paint"
    bl_idname = "SIMPLEPAINT_PT_panel"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        source_collection = utils.get_source_collection(context)

        # -------------------------------------------------
        # SOURCE COLLECTION
        # -------------------------------------------------

        box = layout.box()

        box.prop(
            scene,
            "simplepaint_collection",
            text="Collection"
        )

        if source_collection is None:

            box.label(
                text="Pick a source collection",
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
                bpy.data.collections.get(
                    utils.PLACED_COLLECTION_NAME
                )
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
        # ORIENTATION AND SCALE
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

        # ---- random rotation ----

        box.separator()

        header = box.row(align=True)

        header.label(text="Random Rotation")

        header.prop(
            scene,
            "simplepaint_rot_sync",
            text="Sync",
            toggle=True
        )

        row = box.row(align=True)

        for axis in AXES:

            row.prop(
                scene,
                f"simplepaint_random_rot_{axis}",
                text=AXIS_LABELS[axis],
                toggle=True
            )

        enabled_axes = [
            axis
            for axis in AXES
            if getattr(scene, f"simplepaint_random_rot_{axis}")
        ]

        if scene.simplepaint_rot_sync:

            if enabled_axes:

                # Name the axes the shared range actually drives --
                # labelling it "All" when only Y and Z are on reads
                # like the X axis is being randomized too.
                row = box.row(align=True)

                row.label(
                    text=" ".join(
                        AXIS_LABELS[axis] for axis in enabled_axes
                    )
                )

                row.prop(
                    scene, "simplepaint_rot_min_x", text="Min"
                )

                row.prop(
                    scene, "simplepaint_rot_max_x", text="Max"
                )

        else:

            for axis in enabled_axes:

                row = box.row(align=True)

                row.label(text=AXIS_LABELS[axis])

                row.prop(
                    scene,
                    f"simplepaint_rot_min_{axis}",
                    text="Min"
                )

                row.prop(
                    scene,
                    f"simplepaint_rot_max_{axis}",
                    text="Max"
                )

        # ---- random scale ----

        box.separator()

        header = box.row(align=True)

        header.label(text="Random Scale")

        header.prop(
            scene,
            "simplepaint_scale_sync",
            text="Sync",
            toggle=True
        )

        row = box.row(align=True)

        for axis in AXES:

            row.prop(
                scene,
                f"simplepaint_random_scale_{axis}",
                text=AXIS_LABELS[axis],
                toggle=True
            )

        scale_axes = [
            axis
            for axis in AXES
            if getattr(scene, f"simplepaint_random_scale_{axis}")
        ]

        if scene.simplepaint_scale_sync:

            if scale_axes:

                row = box.row(align=True)

                row.label(
                    text=" ".join(
                        AXIS_LABELS[axis] for axis in scale_axes
                    )
                )

                row.prop(
                    scene, "simplepaint_scale_min_x", text="Min"
                )

                row.prop(
                    scene, "simplepaint_scale_max_x", text="Max"
                )

        else:

            for axis in scale_axes:

                row = box.row(align=True)

                row.label(text=AXIS_LABELS[axis])

                row.prop(
                    scene,
                    f"simplepaint_scale_min_{axis}",
                    text="Min"
                )

                row.prop(
                    scene,
                    f"simplepaint_scale_max_{axis}",
                    text="Max"
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
            "simplepaint_spacing",
            text="Spacing"
        )

        box.prop(
            scene,
            "simplepaint_brush_size",
            text="Brush Size"
        )

        sub = box.column(align=True)

        sub.enabled = scene.simplepaint_paint_mode == 'SURFACE'

        sub.prop(
            scene,
            "simplepaint_show_preview",
            text="Preview Spacing",
            toggle=True,
            icon='SNAP_VERTEX'
        )

        if scene.simplepaint_show_preview:

            sub.prop(
                scene,
                "simplepaint_preview_dot_size",
                text="Dot Size"
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
