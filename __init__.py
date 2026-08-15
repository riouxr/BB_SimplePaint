if "bpy" in locals():
    import importlib
    for mod in [
        utils,
        preview,
        properties,
        operators,
        ui,
    ]:
        importlib.reload(mod)
    print("Add-on Reloaded: BB Simple Paint")
else:
    import bpy
    from . import (
        utils,
        preview,
        properties,
        operators,
        ui,
    )


#### ------------------------------ REGISTRATION ------------------------------ ####

modules = [
    preview,
    properties,
    operators,
    ui,
]


def register():

    for mod in modules:
        mod.register()


def unregister():

    utils.reset_pick_history()

    for mod in reversed(modules):
        mod.unregister()


if __name__ == "__main__":
    register()
