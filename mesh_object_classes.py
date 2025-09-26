import bpy
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
    prefix = obj.name.split("_")[0]
    obj.lod = prefix
    lods = ["LOD1", "LOD2", "LOD3"]
    
    if obj.lod == "SM":
        if obj.name.split("_")[1] == "NITE":
            obj.exportname = obj.name
            obj.lod = "NITE"
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