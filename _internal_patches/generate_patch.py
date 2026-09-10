"""Generate the component_meta patch with embedded original source."""
import base64
import os
PATCH_DIR = os.path.dirname(os.path.abspath(__file__))
ORIG_SOURCE_FILE = os.path.join(PATCH_DIR, "gradio_component_meta_orig.py")
PATCH_FILE = os.path.join(PATCH_DIR, "component_meta.py")
GRADIO_DIR = os.path.join(os.path.dirname(os.__file__), "site-packages", "gradio")
ORIGINAL_CM = os.path.join(GRADIO_DIR, "component_meta.py")

# Step 1: Save original source
print(f"Reading original gradio/component_meta.py from {ORIGINAL_CM}")
with open(ORIGINAL_CM, encoding="utf-8") as f:
    orig_code = f.read()

with open(ORIG_SOURCE_FILE, "w", encoding="utf-8") as f:
    f.write(orig_code)
print(f"Saved original ({len(orig_code)} bytes) → {ORIG_SOURCE_FILE}")

# Step 2: Base64-encode and embed in patch
encoded = base64.b64encode(orig_code.encode("utf-8")).decode("ascii")

patch_template = '''"""Proper patch for gradio/component_meta.py — preserves original EventListener/ComponentMeta."""
from __future__ import annotations
import base64

# Embedded original gradio/component_meta.py source (base64-encoded to survive PyInstaller PYZ)
_ORIG_CODE_B64 = """{b64}"""


def _load_orig():
    return base64.b64decode(_ORIG_CODE_B64).decode("utf-8")


# ── Execute original code in a fresh namespace ──
_ns = {{}}
exec(_load_orig(), _ns)  # type: ignore[reportUnknownVariableType]


# ── Define no-op / safe overrides with distinct names ──
def _noop_create_or_modify_pyi(component_class, class_name, events):
    """No-op: skip writing .py source files from PYZ archive."""
    pass


def _safe_get_local_contexts():
    """Return safe defaults (no Jupyter/Sphinx contexts) for frozen environments."""
    return (False, False)


# ── Patch the namespace BEFORE copying ──
_ns["create_or_modify_pyi"] = _noop_create_or_modify_pyi
_ns["get_local_contexts"] = _safe_get_local_contexts

# ── Copy everything (including patched entries) into this module ──
for _k, _v in _ns.items():
    globals()[_k] = _v  # type: ignore[misc]
'''

patch_code = patch_template.format(b64=encoded)

with open(PATCH_FILE, "w", encoding="utf-8") as f:
    f.write(patch_code)

print(f"Generated patch ({len(patch_code)} bytes) → {PATCH_FILE}")
print("Done!")
