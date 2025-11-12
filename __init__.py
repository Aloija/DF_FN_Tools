import bpy  # type: ignore
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty  # type: ignore

from . import handlers, updater, utils   # <--- новый импорт
from .utils import OBJECT_OT_duplicate_clean_join, OBJECT_OT_rename_uv
from .export import *
from .ui import *


bl_info = {
    "name": "DF FN Tools",
    "description": "DF FN Tools",
    "author": "Aloija, GPT",
    "version": (1, 6, 3),
    "blender": (4, 4, 0),
    "category": "Object"
}


# Addon Preferences с кнопкой обновления
class DFFN_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="GitHub Update")
        row = box.row()
        row.operator("dft.update_from_github", icon="FILE_REFRESH")



# все регистрируемые классы 
classes = (
    DFT_PT_export_panel,
    Exportfbx,
    Open_Folder,
    OBJECT_OT_duplicate_clean_join,
    OBJECT_OT_rename_uv,
    DFFN_AddonPreferences,           # <--- добавлено
    updater.DFT_OT_update_from_github,  # <--- добавлено
)


def register_scene_properties():
    bpy.types.Scene.auto_update_split_vertex_count = BoolProperty(
        name="Auto Update Split Vertex Count",
        default=False,
        description="Automatically update split vertex count on scene changes",
    )

    bpy.types.Scene.split_vertex_count = IntProperty(
        name="Split Vertex Count",
        default=-1,
        description="Number of split vertices based on UV and normals",
    )

    for i in range(utils.MATERIAL_REASSIGN_SLOT_COUNT):
        setattr(
            bpy.types.Scene,
            f"material_from_{i}",
            EnumProperty(
                name=f"Material {i + 1}",
                description="Select a material to reassign",
                items=utils.get_materials,
            ),
        )
        setattr(
            bpy.types.Scene,
            f"material_to_{i}",
            StringProperty(
                name="New Name",
                description="Enter a new material name",
                default="",
            ),
        )


def unregister_scene_properties():
    for i in range(utils.MATERIAL_REASSIGN_SLOT_COUNT):
        from_attr = f"material_from_{i}"
        to_attr = f"material_to_{i}"
        if hasattr(bpy.types.Scene, from_attr):
            delattr(bpy.types.Scene, from_attr)
        if hasattr(bpy.types.Scene, to_attr):
            delattr(bpy.types.Scene, to_attr)

    for attr in ("auto_update_split_vertex_count", "split_vertex_count"):
        if hasattr(bpy.types.Scene, attr):
            delattr(bpy.types.Scene, attr)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    register_scene_properties()
    bpy.types.TOPBAR_MT_editor_menus.append(draw_popover)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_object_context_menu)

    handlers.register_handlers()

def unregister():
    try:
        bpy.types.TOPBAR_MT_editor_menus.remove(draw_popover)
    except (AttributeError, ValueError):
        pass

    try:
        bpy.types.VIEW3D_MT_object_context_menu.remove(draw_object_context_menu)
    except (AttributeError, ValueError):
        pass

    handlers.unregister_handlers()
    unregister_scene_properties()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)



if __name__ == "__main__":
    register()
    GetExportPath()
