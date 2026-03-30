bl_info = {
    "name": "WorldWeaver",
    "blender": (4, 1, 1),
    "category": "Object",
}

import os
import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Operator, AddonPreferences
from bpy_extras.io_utils import ImportHelper

# store keymaps here to access after registration
addon_keymaps = []


class WorldWeaverAddonPreferences(AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    filepath: StringProperty(
        name="Configuration File Path",
        subtype="FILE_PATH",
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="WorldWeaver Preferences:")
        layout.prop(self, "filepath")


class ObjectWorldWeaverConfigSelect(bpy.types.Operator, ImportHelper):
    """Object WorldWeaver Config Select"""

    bl_idname = "object.worldweaver_config_select"
    bl_label = "WorldWeaver Config Select"
    bl_options = {"REGISTER", "UNDO"}
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        """Custom invoke to be able to set the base filepath"""
        preferences = context.preferences
        addon_prefs = preferences.addons[__name__].preferences

        self.filepath = addon_prefs.filepath

        wm = context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        """Change the configuration file for WorldWeaver"""
        preferences = context.preferences
        addon_prefs = preferences.addons[__name__].preferences

        addon_prefs.filepath = self.filepath

        bpy.ops.wm.save_userpref()
        print("Configuration file changed to: ", addon_prefs.filepath)

        return {"FINISHED"}


def menu_func_config_select(self, context):
    self.layout.operator(ObjectWorldWeaverConfigSelect.bl_idname)


class ObjectWorldWeaver(bpy.types.Operator):
    """Object WorldWeaver"""

    bl_idname = "object.worldweaver"
    bl_label = "WorldWeaver"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        # HACK: remove for release
        import sys

        sys.path.append("/home/AVerstraete/Work/worldweaver")

        from worldweaver import main as mpm

        preferences = context.preferences
        addon_prefs = preferences.addons[__name__].preferences

        print("Using config file: ", addon_prefs.filepath)
        mpm.main(addon_prefs.filepath)

        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(ObjectWorldWeaver.bl_idname)


def register():
    bpy.utils.register_class(WorldWeaverAddonPreferences)

    bpy.utils.register_class(ObjectWorldWeaver)
    bpy.types.VIEW3D_MT_object.append(menu_func)

    bpy.utils.register_class(ObjectWorldWeaverConfigSelect)
    bpy.types.VIEW3D_MT_object.append(menu_func_config_select)

    # handle the keymap
    wm = bpy.context.window_manager
    # Note that in background mode (no GUI available), keyconfigs are not available either,
    # so we have to check this to avoid nasty errors in background case.
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name="Object Mode", space_type="EMPTY")
        kmi = km.keymap_items.new(
            ObjectWorldWeaver.bl_idname, "M", "PRESS", ctrl=True, shift=True
        )
        addon_keymaps.append((km, kmi))

        km2 = wm.keyconfigs.addon.keymaps.new(name="Object Mode", space_type="EMPTY")
        kmi2 = km2.keymap_items.new(
            ObjectWorldWeaverConfigSelect.bl_idname, "L", "PRESS", ctrl=True, shift=True
        )
        addon_keymaps.append((km2, kmi2))


def unregister():
    # Note: when unregistering, it's usually good practice to do it in reverse order you registered.
    # Can avoid strange issues like keymap still referring to operators already unregistered...
    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(ObjectWorldWeaverConfigSelect)
    bpy.types.VIEW3D_MT_object.remove(menu_func_config_select)

    bpy.utils.unregister_class(ObjectWorldWeaver)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

    bpy.utils.unregister_class(WorldWeaverAddonPreferences)


if __name__ == "__main__":
    register()
