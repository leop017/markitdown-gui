"""Generate the pyinstaller runtime hook with embedded patched component_meta."""
import base64
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "component_meta.py")
HOOK_FILE = os.path.join(PROJECT_ROOT, "_pyinstaller_runtime_hook.py")

with open(PATCH_FILE, "r", encoding="utf-8") as f:
    patch_code = f.read()

encoded = base64.b64encode(patch_code.encode("utf-8")).decode("ascii")

hook_template = '''"""PyInstaller runtime hook — patches gradio.component_meta at import time."""
import sys
import types
import base64

_PATCHED_CODE_B64 = """$(B64)"""

class _GradioMetaPathFinder:
    """Intercepts imports of gradio.component_meta to inject the patched version."""
    def find_module(self, fullname, path=None):
        if fullname == "gradio.component_meta":
            return self
        return None

    def load_module(self, fullname):
        code = base64.b64decode(_PATCHED_CODE_B64).decode("utf-8")
        mod = types.ModuleType(fullname)
        mod.__file__ = "gradio/component_meta.py"
        mod.__loader__ = self
        mod.__package__ = "gradio"
        exec(code, mod.__dict__)  # type: ignore[reportUnknownVariableType]
        sys.modules[fullname] = mod
        return mod

# Remove any previous instance
for _finder in list(sys.meta_path):
    if type(_finder).__name__ == "_GradioMetaPathFinder":
        sys.meta_path.remove(_finder)
sys.meta_path.insert(0, _GradioMetaPathFinder())
print("[runtime_hook] gradio.component_meta meta-path hook installed", flush=True)
'''

hook_code = hook_template.replace("$(B64)", encoded)

with open(HOOK_FILE, "w", encoding="utf-8") as f:
    f.write(hook_code)

print(f"Generated runtime hook ({len(hook_code)} bytes)")
