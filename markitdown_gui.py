import os
import logging
import webbrowser
import threading
import socket
import time

# ── PyInstaller onefile fix (handled by _pyinstaller_runtime_hook.py) ────────
# The runtime hook patches Path.read_text and gradio.component_meta.create_or_modify_pyi
# BEFORE any gradio import. See _pyinstaller_runtime_hook.py for details.
import gradio as gr

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("gradio").setLevel(logging.WARNING)

# ── Logging hardening for windowed (console=False) builds ──────────────────────
import logging.config as _logging_config
_orig_dict_config = _logging_config.dictConfig

def _safe_dict_config(cfg):
    try:
        formatters = (cfg or {}).get("formatters") or {}
        for name, entry in list(formatters.items()):
            if isinstance(entry, dict) and ("()" in entry or "class" in entry):
                fmt = entry.get("fmt") or "%(levelname)s %(name)s: %(message)s"
                datefmt = entry.get("datefmt")
                formatters[name] = {
                    "format": fmt,
                    "datefmt": datefmt,
                }
    except Exception:
        pass
    return _orig_dict_config(cfg)

_logging_config.dictConfig = _safe_dict_config

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

from markitdown import MarkItDown, UnsupportedFormatException, FileConversionException

md = MarkItDown()

_server_port = 7860

# ── LLM helpers ──────────────────────────────────────────────────────────────
def _build_llm_kwargs(enable_llm, llm_base_url, llm_api_key, llm_model, llm_prompt=""):
    kwargs = {}
    if enable_llm and llm_base_url and llm_api_key and llm_model:
        try:
            import openai
            kwargs["llm_client"] = openai.OpenAI(
                base_url=llm_base_url,
                api_key=llm_api_key,
            )
            kwargs["llm_model"] = llm_model
            if llm_prompt:
                kwargs["llm_prompt"] = llm_prompt
        except Exception:
            pass
    return kwargs


def _convert_single(path, enable_llm=False, llm_base_url="", llm_api_key="", llm_model="", enable_plugins=False, llm_prompt=""):
    kwargs = {"enable_plugins": enable_plugins}
    kwargs.update(_build_llm_kwargs(enable_llm, llm_base_url, llm_api_key, llm_model, llm_prompt))
    local_md = MarkItDown(**kwargs)
    try:
        t0 = time.perf_counter()
        result = local_md.convert(path)
        elapsed = time.perf_counter() - t0
        return (result.markdown if result else "", None, elapsed)
    except UnsupportedFormatException as e:
        return ("", f"不支持的格式: {e}", 0)
    except FileConversionException as e:
        return ("", f"转换失败: {e}", 0)
    except Exception as e:
        return ("", f"错误: {type(e).__name__}: {e}", 0)


def convert_file(file_obj, enable_llm=False, llm_base_url="", llm_api_key="", llm_model="", enable_plugins=False, llm_prompt=""):
    if file_obj is None:
        yield "[请上传一个文件]", "", "未选择文件", "—"
        return

    paths = file_obj if isinstance(file_obj, list) else [file_obj]
    paths = [p.name if hasattr(p, "name") else p for p in paths]

    parts = []
    total_chars = 0
    total_elapsed = 0.0
    for i, path in enumerate(paths, 1):
        yield "", "", f"处理 {i}/{len(paths)}: {os.path.basename(path)}", "—"
        text, err, elapsed = _convert_single(path, enable_llm=enable_llm, llm_base_url=llm_base_url, llm_api_key=llm_api_key, llm_model=llm_model, enable_plugins=enable_plugins, llm_prompt=llm_prompt)
        if err:
            parts.append(f"## ⚠️ {os.path.basename(path)}\n\n_{err}_\n")
            yield "\n\n".join(parts), "\n\n".join(parts), f"⚠️ {err}", f"{total_chars} 字符 · {total_elapsed:.2f}s"
        else:
            parts.append(f"## 📄 {os.path.basename(path)}\n\n{text}\n")
            total_chars += len(text)
            total_elapsed += elapsed
            yield "\n\n".join(parts), "\n\n".join(parts), "成功", f"{total_chars} 字符 · {total_elapsed:.2f}s"

    if not parts:
        yield "[没有可处理的文件]", "", "没有可处理的文件", "—"

def convert_urls(urls: str):
    lines = [line.strip() for line in (urls or "").splitlines() if line.strip()]
    if not lines:
        yield "[请输入 URL]", "", "URL 为空", "—"
        return

    parts = []
    total_chars = 0
    total_elapsed = 0.0
    for i, url in enumerate(lines, 1):
        yield "", "", f"正在抓取 {i}/{len(lines)}: {url[:60]} ...", "—"
        try:
            t0 = time.perf_counter()
            result = md.convert(url)
            elapsed = time.perf_counter() - t0
            text = result.markdown if result else ""
            parts.append(f"## 🌐 {url}\n\n{text}\n")
            total_chars += len(text)
            total_elapsed += elapsed
            yield "\n\n".join(parts), "\n\n".join(parts), "成功", f"{total_chars} 字符 · {total_elapsed:.2f}s"
        except Exception as e:
            parts.append(f"## ⚠️ {url}\n\n_{type(e).__name__}: {e}_\n")
            yield "\n\n".join(parts), "\n\n".join(parts), f"失败 ({i}/{len(lines)}): {type(e).__name__}", f"{total_chars} 字符 · {total_elapsed:.2f}s"

    if not parts:
        yield "[没有可处理的 URL]", "", "没有可处理的 URL", "—"


# ── Open URL in browser ───────────────────────────────────────────────────────
def open_web():
    threading.Thread(
        target=lambda: webbrowser.open(f"http://127.0.0.1:{_server_port}/"), daemon=True
    ).start()

# ── Download handler ───────────────────────────────────────────────────────────
def _download_markdown(md_text, ext="md"):
    if not md_text or not md_text.strip():
        return gr.Button(visible=False)
    try:
        import sys
        if getattr(sys, "frozen", False):
            # 冻结 EXE：固定保存到可执行文件所在目录，避免随 CWD 漂移
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = "markitdown_output"
        ts = time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(base_dir, f"{filename}_{ts}.{ext}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_text)
        try:
            os.startfile(os.path.dirname(filepath))
        except OSError:
            pass
    except Exception:
        pass
    return gr.Button(visible=False)


def on_download(md_text):
    _download_markdown(md_text)


def _show_download_if_content(md_text):
    visible = bool(md_text and md_text.strip() and not md_text.strip().startswith("等待"))
    return gr.Button(visible=visible)


# ── LLM 连通性检测 ─────────────────────────────────────────────────────────────
def on_test_llm(llm_base_url, llm_api_key, llm_model):
    """向配置的 LLM 端点发送一次最小请求，返回连接状态。"""
    if not llm_base_url or not llm_api_key or not llm_model:
        return "❌ 请先填写 Base URL、API Key 和模型名称"
    try:
        import openai
        client = openai.OpenAI(base_url=llm_base_url, api_key=llm_api_key)
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        elapsed = time.perf_counter() - t0
        choice = resp.choices[0] if resp.choices else None
        return f"✅ 连接成功 · {elapsed:.1f}s · 模型: {llm_model}" + (
            f"\n响应: {choice.message.content.strip()[:80]}" if choice else ""
        )
    except Exception as e:
        return f"❌ 连接失败 · {type(e).__name__}: {e}"


# ── Build UI ───────────────────────────────────────────────────────────────────
_CSS = """
/* ── Hero / title ─────────────────────────────────────────────────────────── */
.hero {
    text-align: center;
    padding: 1.5rem 0 0.75rem;
}
.hero-title {
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 0.3rem;
    color: var(--color-text);
    letter-spacing: -0.02em;
}
.hero-sub {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    max-width: 42rem;
    margin: 0 auto;
    line-height: 1.6;
}

/* ── Cards ────────────────────────────────────────────────────────────────── */
.card {
    background: var(--color-background);
    border: 1px solid var(--color-border-primary);
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

/* ── Drop area ────────────────────────────────────────────────────────────── */
.drop-area {
    border: 2px dashed var(--color-accent-300, #94a3b8) !important;
    border-radius: 12px !important;
    padding: 1.5rem 1rem !important;
    text-align: center;
    background: var(--color-background-soft) !important;
    transition: border-color 0.2s, background 0.2s;
    cursor: pointer;
}
.drop-area:hover {
    border-color: var(--color-accent-500, #3b82f6) !important;
    background: var(--color-background-secondary) !important;
}

/* ── Status / info boxes ──────────────────────────────────────────────────── */
.status-box {
    font-size: 0.85em !important;
    padding: 0.45rem 0.7rem !important;
    border-radius: 6px !important;
    background: var(--color-background-soft) !important;
    border: 1px solid var(--color-border-primary) !important;
    color: var(--color-text);
    font-family: var(--font-code, monospace);
    font-weight: 500;
}
.status-box.success { background: #f0fdf4 !important; border-color: #bbf7d0 !important; color: #166534 !important; }
.status-box.error   { background: #fef2f2 !important; border-color: #fecaca !important; color: #991b1b !important; }

.char-count {
    font-size: 0.78em;
    color: var(--color-text-secondary);
    text-align: right;
    font-family: var(--font-code, monospace);
}

/* ── LLM status text ─────────────────────────────────────────────────────── */
.llm-status {
    font-size: 0.82em !important;
    font-family: var(--font-code, monospace);
}

/* ── Tabs polish ──────────────────────────────────────────────────────────── */
.gradio-tabs > div > div:nth-child(1) {
    gap: 0.25rem !important;
}

/* ── Footer ───────────────────────────────────────────────────────────────── */
.footer {
    text-align: center;
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    padding: 1.2rem 0 0.75rem;
    line-height: 1.8;
}
.footer a { color: var(--color-accent-500); text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.gr-button.primary {
    font-weight: 600 !important;
    border-radius: 8px !important;
}

/* ── Row / column spacing ─────────────────────────────────────────────────── */
.opt-row { gap: 0.6rem !important; }

/* ── Output area ─────────────────────────────────────────────────────────── */
.output-panel {
    background: var(--color-background-soft) !important;
    border-radius: 8px !important;
    border: 1px solid var(--color-border-primary) !important;
}
"""

with gr.Blocks(
    title="MarkItDown",
    theme=gr.themes.Soft(),
    css=_CSS,
) as app:

    # ── Hero ──────────────────────────────────────────────────────────────────
    gr.HTML(
        '<div class="hero">'
        '<div class="hero-title">📄 MarkItDown</div>'
        '<div class="hero-sub">'
        '支持 <b>Word · PDF · PPT · Excel · 图片 · 音频 · 网页 · HTML · Markdown · CSV · EPUB · ZIP · 邮件 · Jupyter</b> 等格式，'
        '可启用自定义 LLM 图片描述或第三方 OCR 插件'
        '</div></div>'
    )

    with gr.Tabs():

        # ═══════════ Tab 1：文件转换 ═══════════════════════════════════════
        with gr.Tab("📁 文件转换"):
            with gr.Row(equal_height=False):

                # ── 左列：上传区 + 选项 ─────────────────────────────────────
                with gr.Column(scale=1, elem_classes=["card"]):
                    file_input = gr.File(
                        label=None,
                        file_count="multiple",
                        type="filepath",
                        elem_classes=["drop-area"],
                    )
                    gr.HTML('<div style="font-size:0.8em;color:var(--color-text-secondary);text-align:center;margin-top:0.3rem;">支持拖放 · 可批量上传</div>')

                    with gr.Accordion("⚙️ 转换选项", open=False):
                        enable_llm_cb = gr.Checkbox(
                            label="使用 LLM 描述图片",
                            value=False,
                            info="启用后自动对图片调用 LLM 生成描述",
                        )
                        enable_plugins_cb = gr.Checkbox(
                            label="启用第三方插件（OCR 等）",
                            value=False,
                            info="需要已安装 markitdown-ocr 等插件",
                        )

                        with gr.Accordion("🔗 LLM 连接配置", open=False):
                            llm_base_url_inp = gr.Textbox(
                                label="接口地址（Base URL）",
                                placeholder="https://api.openai.com/v1",
                                info="支持任意 OpenAI 兼容接口（vLLM / 硅基流动 / LocalAI 等）",
                            )
                            llm_api_key_inp = gr.Textbox(
                                label="密钥（API Key）",
                                placeholder="sk-...",
                                type="password",
                            )
                            llm_model_inp = gr.Textbox(
                                label="模型名称",
                                placeholder="gpt-4o",
                                info="例如 gpt-4o、deepseek-v3、llama-3.2-vision",
                            )
                            llm_prompt_inp = gr.Textbox(
                                label="自定义 Prompt（可选）",
                                placeholder="例如：请用中文详细描述这张图片",
                                info="留空则使用默认英文 prompt",
                                lines=2,
                            )
                            with gr.Row(elem_classes=["opt-row"]):
                                test_llm_btn = gr.Button("测试连接", size="sm", variant="secondary")
                                llm_status_txt = gr.Textbox(
                                    label=None, value="", interactive=False,
                                    max_lines=3, elem_classes=["llm-status"],
                                )
                            test_llm_btn.click(
                                fn=on_test_llm,
                                inputs=[llm_base_url_inp, llm_api_key_inp, llm_model_inp],
                                outputs=[llm_status_txt],
                            )

                    with gr.Row(equal_height=False):
                        convert_btn = gr.Button("⚡ 开始转换", variant="primary", size="lg")
                        download_btn = gr.Button(
                            "💾 下载 .md", size="sm",
                            variant="secondary", visible=False,
                        )

                # ── 右列：输出区 ────────────────────────────────────────────
                with gr.Column(scale=2, elem_classes=["card"]):
                    with gr.Tabs():
                        with gr.Tab("📝 Markdown 预览"):
                            md_output = gr.Markdown(value="等待上传文件…", show_copy_button=True)
                        with gr.Tab("📋 纯文本"):
                            txt_output = gr.Textbox(
                                label=None,
                                lines=15, max_lines=40,
                                show_copy_button=True,
                                interactive=False,
                                elem_classes=["output-panel"],
                            )
                    with gr.Row(equal_height=False, elem_classes=["opt-row"]):
                        status_text = gr.Textbox(
                            label=None, value="就绪", interactive=False,
                            elem_classes=["status-box"], scale=2,
                        )
                        char_count = gr.Textbox(
                            label=None, value="—", interactive=False,
                            max_lines=1, elem_classes=["char-count"], scale=1,
                        )

            convert_btn.click(
                fn=convert_file,
                inputs=[file_input, enable_llm_cb, llm_base_url_inp, llm_api_key_inp, llm_model_inp, enable_plugins_cb, llm_prompt_inp],
                outputs=[md_output, txt_output, status_text, char_count],
            )
            md_output.change(
                fn=_show_download_if_content,
                inputs=[md_output],
                outputs=[download_btn],
            )
            txt_output.change(
                fn=_show_download_if_content,
                inputs=[txt_output],
                outputs=[download_btn],
            )
            download_btn.click(
                fn=on_download,
                inputs=[md_output],
            )

        # ═══════════ Tab 2：网页 / URL 抓取 ════════════════════════════════
        with gr.Tab("🌐 网页 / URL 抓取"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=1, elem_classes=["card"]):
                    url_input = gr.Textbox(
                        label="网页地址",
                        placeholder="每行一个 URL，支持批量抓取\nhttps://example.com/article\nhttps://en.wikipedia.org/wiki/Python",
                        lines=5,
                        elem_classes=["output-panel"],
                    )
                    with gr.Row():
                        fetch_btn = gr.Button("🚀 抓取并转换", variant="primary", size="lg")
                        url_download_btn = gr.Button(
                            "💾 下载 .md", size="sm",
                            variant="secondary", visible=False,
                        )

                with gr.Column(scale=2, elem_classes=["card"]):
                    with gr.Tabs():
                        with gr.Tab("📝 Markdown 预览"):
                            url_md = gr.Markdown(value="等待抓取…", show_copy_button=True)
                        with gr.Tab("📋 纯文本"):
                            url_txt = gr.Textbox(
                                label=None, lines=15, max_lines=40,
                                show_copy_button=True, interactive=False,
                                elem_classes=["output-panel"],
                            )
                    with gr.Row(equal_height=False, elem_classes=["opt-row"]):
                        url_status = gr.Textbox(
                            label=None, value="就绪", interactive=False,
                            elem_classes=["status-box"], scale=2,
                        )
                        url_chars = gr.Textbox(
                            label=None, value="—", interactive=False,
                            max_lines=1, elem_classes=["char-count"], scale=1,
                        )

            fetch_btn.click(
                fn=convert_urls,
                inputs=[url_input],
                outputs=[url_md, url_txt, url_status, url_chars],
            )

            url_md.change(fn=_show_download_if_content, inputs=[url_md], outputs=[url_download_btn])
            url_txt.change(fn=_show_download_if_content, inputs=[url_txt], outputs=[url_download_btn])
            url_download_btn.click(fn=on_download, inputs=[url_md])

    # ── Bottom bar ────────────────────────────────────────────────────────────
    with gr.Row(elem_classes=["footer"]):
        gr.HTML(
            '<div style="width:100%;">'
            '<span style="margin-right:1rem;">Powered by '
            '<a href="https://github.com/microsoft/markitdown" target="_blank">Microsoft MarkItDown</a>'
            ' · Gradio</span>'
            '</div>'
        )
    open_btn = gr.Button("🌐 在浏览器中打开", size="sm", variant="secondary")
    open_btn.click(fn=open_web)

# ── Main entry point ───────────────────────────────────────────────────────────
def _kill_old_instances():
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_TERMINATE = 0x0001
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")
        EnumProcesses = psapi.EnumProcesses
        EnumProcesses.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
        EnumProcesses.restype = wintypes.BOOL
        GetModuleFileNameExW = psapi.GetModuleFileNameExW
        GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                         wintypes.LPWSTR, wintypes.DWORD]
        GetModuleFileNameExW.restype = wintypes.DWORD
        OpenProcess = kernel32.OpenProcess
        OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        OpenProcess.restype = wintypes.HANDLE
        TerminateProcess = kernel32.TerminateProcess
        TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        TerminateProcess.restype = wintypes.BOOL
        CloseHandle = kernel32.CloseHandle
        CloseHandle.argtypes = [wintypes.HANDLE]
        CloseHandle.restype = wintypes.BOOL

        buf = (ctypes.c_uint * 4096)()
        cb = ctypes.c_uint()
        if not EnumProcesses(ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(cb)):
            return
        n = cb.value // ctypes.sizeof(ctypes.c_uint)
        my_pid = os.getpid()
        target_substrings = ("markitdown.exe", "markitdown_gui.py",
                             "markitdown_gui.exe")
        for i in range(n):
            pid = buf[i]
            if pid == 0 or pid == my_pid:
                continue
            h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE,
                            False, pid)
            if not h:
                continue
            try:
                name_buf = ctypes.create_unicode_buffer(1024)
                if GetModuleFileNameExW(h, None, name_buf, 1024):
                    basename = os.path.basename(name_buf.value or "").lower()
                    if any(s in basename for s in target_substrings):
                        TerminateProcess(h, 1)
            finally:
                CloseHandle(h)
    except Exception:
        pass


def _port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return False
    except OSError:
        return True


def _find_free_port(start: int = 7860, attempts: int = 20) -> int:
    for p in range(start, start + attempts):
        if _port_is_free(p):
            return p
    return start


if __name__ == "__main__":
    def _log_startup_error(prefix: str, exc: BaseException):
        try:
            import traceback as _tb
            err_file = os.path.join(os.path.dirname(__file__), "startup_error.log")
            with open(err_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{prefix}] {type(exc).__name__}: {exc}\n")
                f.write(_tb.format_exc())
        except Exception:
            pass

    def _setup_server():
        global _server_port
        env_port = os.environ.get("GRADIO_SERVER_PORT")
        if env_port and env_port.isdigit():
            port = int(env_port)
        else:
            port = _find_free_port(7860, 20)
            if port != 7860:
                try:
                    port_file = os.path.join(os.path.dirname(__file__), "current_port.txt")
                    with open(port_file, "w", encoding="utf-8") as f:
                        f.write(str(port))
                except Exception:
                    pass
        _server_port = port
        return port

    try:
        _kill_old_instances()
    except BaseException as e:
        _log_startup_error("_kill_old_instances", e)

    port = _setup_server()

    def _open_browser():
        time.sleep(3.0)
        try:
            webbrowser.open(f"http://127.0.0.1:{port}/", new=1, autoraise=True)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    print(f"MarkItDown GUI 正在启动：http://127.0.0.1:{port}/")
    print("若浏览器未自动打开，请在浏览器中访问上方网址。")

    def _retry_launch(failed_port: int):
        global _server_port
        port = _find_free_port(failed_port + 1, 10)
        _server_port = port
        app.launch(
            server_name="127.0.0.1",
            server_port=port,
            show_error=True,
            quiet=True,
            inbrowser=False,
        )

    try:
        app.launch(
            server_name="127.0.0.1",
            server_port=port,
            show_error=True,
            quiet=True,
            inbrowser=False,
        )
    except OSError as e:
        _log_startup_error("OSError", e)
        if "Cannot find empty port" in str(e) or "address already in use" in str(e).lower():
            _retry_launch(port)
        else:
            raise
    except BaseException as e:
        _log_startup_error("app.launch", e)
        raise
