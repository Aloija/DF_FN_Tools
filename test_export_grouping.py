import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


def load_function(filename, function_name, namespace):
    source = Path(__file__).with_name(filename).read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    exec(compile(ast.Module(body=[function], type_ignores=[]), filename, "exec"), namespace)
    return namespace[function_name]


class ExportGroupingTests(unittest.TestCase):
    def test_any_numeric_lod_joins_only_when_enabled_and_lod0_exists(self):
        namespace = {}
        is_lod_name = load_function("mesh_object_classes.py", "is_lod_name", namespace)
        group_name = load_function("export.py", "get_export_group_name", namespace)
        lod12 = SimpleNamespace(lod="LOD12", exportname="SM_Chair_LOD12")

        self.assertTrue(is_lod_name("LOD12"))
        self.assertFalse(is_lod_name("LODA"))
        self.assertEqual(group_name(lod12, False, {"SM_Chair"}), "SM_Chair_LOD12")
        self.assertEqual(group_name(lod12, True, {"SM_Chair"}), "SM_Chair")
        self.assertEqual(group_name(lod12, True, set()), "SM_Chair_LOD12")

        namespace["MeshObject"] = object
        obj_init = load_function("mesh_object_classes.py", "obj_init", namespace)
        mesh = SimpleNamespace(name="LOD12_SM_Chair", lod=None, exportname=None)
        obj_init(mesh)
        self.assertEqual(mesh.exportname, "SM_Chair_LOD12")


if __name__ == "__main__":
    unittest.main()
