"""Third-party markitdown plugin detection."""


def _detect_installed_plugins():
    """Return installed markitdown plugin names (via entry points)."""
    try:
        from importlib.metadata import entry_points
        names = [ep.name for ep in entry_points(group="markitdown.plugin")]
        return sorted(set(names))
    except Exception:
        return []


def on_plugin_toggle(checked):
    """When 'Enable plugins' is checked, show detected plugins and LLM hints."""
    if not checked:
        return ""
    plugins = _detect_installed_plugins()
    if not plugins:
        return "⚠️ 未检测到任何 markitdown 插件（markitdown.plugin 入口点为空）。"
    names = "、".join(plugins)
    return (
        f"✅ 已启用插件：{names}。"
        "markitdown-ocr 需配合「使用 LLM 描述图片」填写 LLM 参数，未填写时 OCR 会被跳过。"
    )
