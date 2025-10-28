# updater.py
import bpy # type: ignore
import os
import sys
import shutil
import tempfile
import zipfile
import urllib.request


def _addon_root():
    # Папка модуля аддона (верхняя директория пакета)
    import importlib
    pkg = __package__.split('.')[0] if __package__ else __name__.split('.')[0]
    mod = importlib.import_module(pkg)
    return os.path.dirname(os.path.abspath(mod.__file__))

def _copy_tree(src, dst):
    # Копируем содержимое src в dst поверх существующего
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            src_f = os.path.join(root, f)
            dst_f = os.path.join(target_dir, f)
            shutil.copy2(src_f, dst_f)

class DFT_OT_update_from_github(bpy.types.Operator):
    """Скачать и установить последнюю версию из main ветки"""
    bl_idname = "dft.update_from_github"
    bl_label = "Update from GitHub (main)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons.get(__package__.split('.')[0]).preferences
        repo_zip_url = prefs.repo_zip_url or "https://github.com/Aloija/DF_FN_Tools/archive/refs/heads/main.zip"
        addon_root = _addon_root()

        self.report({'INFO'}, "Downloading update...")
        tmpdir = tempfile.mkdtemp(prefix="dffn_update_")
        zip_path = os.path.join(tmpdir, "main.zip")

        try:
            # 1) Скачать архив
            urllib.request.urlretrieve(repo_zip_url, zip_path)

            # 2) Распаковать
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmpdir)

            # GitHub кладет внутри папку <repo>-main, ищем её
            extracted_root = None
            for name in os.listdir(tmpdir):
                full = os.path.join(tmpdir, name)
                if os.path.isdir(full) and name.endswith("-main"):
                    extracted_root = full
                    break
            if not extracted_root:
                raise RuntimeError("Не удалось найти распакованную директорию репозитория")

            # 3) Скопировать поверх текущего аддона
            # Исключим .git, .github, .vscode, __pycache__ ради гигиены
            for junk in (".git", ".github", ".vscode", "__pycache__"):
                junk_path = os.path.join(extracted_root, junk)
                if os.path.exists(junk_path):
                    shutil.rmtree(junk_path, ignore_errors=True)

            _copy_tree(extracted_root, addon_root)

            # 4) Попробовать горячую перезагрузку аддона
            pkg_name = __package__.split('.')[0] if __package__ else __name__.split('.')[0]
            try:
                bpy.ops.preferences.addon_disable(module=pkg_name)
            except Exception:
                pass
            try:
                bpy.ops.preferences.addon_enable(module=pkg_name)
            except Exception:
                pass

            self.report({'INFO'}, "DF_FN_Tools обновлен из main")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Update failed: {e}")
            return {'CANCELLED'}

        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
