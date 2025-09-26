import bpy
from .export import *
from .ui import *
from . import updater   # <--- новый импорт
from bpy.props import IntProperty, BoolProperty, StringProperty


bl_info = {
    "name": "DF FN Tools",
    "description": "DF FN Tools",
    "author": "Aloija, GPT",
    "version": (1, 5, 3),
    "blender": (4, 4, 0),
    "category": "Object"
}


# Addon Preferences с кнопкой обновления
class DFFN_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    repo_zip_url: StringProperty(
        name="ZIP URL",
        description="Ссылка на ZIP main ветки репозитория",
        default="https://github.com/Aloija/DF_FN_Tools/archive/refs/heads/main.zip"
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="GitHub Update")
        box.prop(self, "repo_zip_url")
        row = box.row()
        row.operator("dft.update_from_github", icon="FILE_REFRESH")


# все регистрируемые классы
classes = (
    DFT_PT_export_panel,
    Exportfbx,
    Open_Folder,
    DFFN_AddonPreferences,           # <--- добавлено
    updater.DFT_OT_update_from_github,  # <--- добавлено
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.auto_update_split_vertex_count = BoolProperty(
        name="Auto Update Split Vertex Count",
        default=False,
        description="Automatically update split vertex count on scene changes"
    )

    bpy.types.Scene.split_vertex_count = IntProperty(
        name="Split Vertex Count",
        default=-1,
        description="Number of split vertices based on UV and normals"
    )

    bpy.types.TOPBAR_MT_editor_menus.append(draw_popover)

    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update)


def unregister():
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_popover)

    bpy.app.handlers.load_post.remove(load_handler)
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
    GetExportPath()
