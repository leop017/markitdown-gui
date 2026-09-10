"""Download / save handlers for Markdown output."""
import os
import time

import gradio as gr


def _base_dir() -> str:
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # In source mode __file__ is mdgui/downloader.py, so parent of mdgui/ is project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _download_markdown(md_text, ext="md"):
    if not md_text or not md_text.strip():
        return gr.Button(visible=False)
    try:
        base_dir = _base_dir()
        filename = "markitdown_output"
        ts = time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(base_dir, f"{filename}_{ts}.{ext}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_text)
        try:
            os.startfile(os.path.dirname(filepath))
        except (OSError, AttributeError):
            pass
    except Exception:
        pass
    return gr.Button(visible=False)


def on_download(md_text):
    _download_markdown(md_text)


def _show_download_if_content(md_text):
    visible = bool(md_text and md_text.strip() and not md_text.strip().startswith("等待"))
    return gr.Button(visible=visible)
