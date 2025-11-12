# handlers.py
import bpy
from bpy.app.handlers import persistent

from .utils import update_split_vertex_count


@persistent
def load_handler(dummy):
    scene = bpy.context.scene
    if scene and getattr(scene, "auto_update_split_vertex_count", False):
        update_split_vertex_count(scene)


@persistent
def depsgraph_update(scene, depsgraph):
    context_scene = bpy.context.scene
    if context_scene and getattr(context_scene, "auto_update_split_vertex_count", False):
        update_split_vertex_count(context_scene)


def register_handlers():
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)
    if depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update)


def unregister_handlers():
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    if depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update)
