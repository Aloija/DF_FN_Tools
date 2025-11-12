from dataclasses import dataclass, field
from typing import Optional

import bpy  # type: ignore


@dataclass
class MeshObject:
    bl_object: bpy.types.Object
    exportname: Optional[str] = None
    lod: Optional[str] = None
    valid: bool = True
    orig_name: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.orig_name = self.bl_object.name

    @property
    def name(self) -> str:
        return self.bl_object.name

    @name.setter
    def name(self, value: str) -> None:
        self.bl_object.name = value
        mesh = self.mesh
        if mesh and hasattr(mesh, "name"):
            mesh.name = value

    @property
    def mesh(self) -> bpy.types.Mesh:
        return self.bl_object.data

    def select_set(self, state: bool) -> None:
        self.bl_object.select_set(state)

    def hide_set(self, state: bool) -> None:
        self.bl_object.hide_set(state)


def obj_init(mesh_obj: MeshObject) -> None:
    name_parts = mesh_obj.name.split("_")
    prefix = name_parts[0]
    second_part = name_parts[1] if len(name_parts) > 1 else None
    mesh_obj.lod = prefix
    lods = ["LOD1", "LOD2", "LOD3"]
    
    if (prefix == "SM" and second_part == "NITE"):
        mesh_obj.exportname = mesh_obj.name
        mesh_obj.lod = "NITE"
        return
    if mesh_obj.lod == "LOD0":
        mesh_obj.exportname = mesh_obj.name[5:]
        return
    if mesh_obj.lod in lods:
        mesh_obj.exportname = (mesh_obj.name[5:] + "_" + mesh_obj.lod)
    if mesh_obj.lod == "UCX":
        mesh_obj.exportname = mesh_obj.name[9:-3]
    else:
        pass
    return


def save_selected() -> list[MeshObject]:
    context = bpy.context
    selected: list[MeshObject] = []
    for obj in context.selected_objects:
        objitem = MeshObject(obj)
        selected.append(objitem)
    return selected
