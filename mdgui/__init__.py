"""mdgui - MarkItDown GUI package.

Logging hardening must run before any gradio import.
"""
import logging
import logging.config as _logging_config

# Silence noisy loggers before gradio pulls them in
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("gradio").setLevel(logging.WARNING)

# ── Logging hardening for windowed (console=False) builds ──────────────────────
# Gradio's internal dictConfig uses factory-style formatter entries that crash
# when there is no console (PyInstaller onefile, console=False).  Patch
# dictConfig to strip those entries before the original runs.
_orig_dict_config = _logging_config.dictConfig


def _safe_dict_config(cfg):
    try:
        formatters = (cfg or {}).get("formatters") or {}
        for name, entry in list(formatters.items()):
            if isinstance(entry, dict) and ("()" in entry or "class" in entry):
                formatters[name] = {
                    "format": entry.get("fmt") or "%(levelname)s %(name)s: %(message)s",
                    "datefmt": entry.get("datefmt"),
                }
    except Exception:
        pass
    return _orig_dict_config(cfg)


_logging_config.dictConfig = _safe_dict_config

# Remove stale handlers, then set a sane root config
try:
    _root = logging.getLogger()
    for _h in list(_root.handlers):
        try:
            _root.removeHandler(_h)
        except Exception:
            pass
except Exception:
    pass
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
