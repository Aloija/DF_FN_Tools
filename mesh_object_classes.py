import bpy # type: ignore
from .utils import *

class MehsObject:
    def __init__ (self, obj: bpy.types.Object):
        self.data = obj
        self.name = obj.name
        self.orig_name = obj.name
        self.exportname = None
        self.lod = None
        self.valid = True


def obj_init(obj): 
    name_parts = obj.name.split("_")
    prefix = name_parts[0]
    second_part = name_parts[1] if len(name_parts) > 1 else None
    obj.lod = prefix
    lods = ["LOD1", "LOD2", "LOD3"]
    
    if (prefix == "SM" and second_part == "NITE"):
        obj.exportname = obj.name
        obj.lod = "NITE"
        return
    if obj.lod == "LOD0":
        obj.exportname = obj.name[5:]
        return
    if obj.lod in lods:
        obj.exportname = (obj.name[5:] + "_" + obj.lod)
    if obj.lod == "UCX":
        obj.exportname = obj.name[9:-3]
    else:
        pass
    return


def save_selected():
        context = bpy.context
        selected = []
        for obj in context.selected_objects:
            objitem = MehsObject(obj)
            selected.append(objitem)
        return selected
