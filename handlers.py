# handlers.py
import bpy
from bpy.app.handlers import persistent
from .utils import update_split_vertex_count

@persistent
def load_handler(dummy):
    print("Blend-файл загружен:", bpy.data.filepath)
    context_scene = bpy.context.scene
    if context_scene and getattr(context_scene, "auto_update_split_vertex_count", False):
        update_split_vertex_count(context_scene)

@persistent
def depsgraph_update(scene, depsgraph):
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update)
    update_split_vertex_count(bpy.context.scene)
    pass
