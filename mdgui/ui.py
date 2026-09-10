"""Gradio UI construction."""
import threading
import webbrowser

import gradio as gr

from .converter import convert_file, convert_urls
from .downloader import _show_download_if_content, on_download
from .llm import on_test_llm
from .plugins import on_plugin_toggle

# ── Mutable port (read at click time, so retries update the browser URL) ─────
_server_port = 7860


def _set_port(port: int):
    global _server_port
    _server_port = port


def _get_port() -> int:
    return _server_port


def open_web():
    port = _get_port()
    threading.Thread(
        target=lambda: webbrowser.open(f"http://127.0.0.1:{port}/"), daemon=True
    ).start()


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


def build_ui():
    with gr.Blocks(
        title="MarkItDown",
        theme=gr.themes.Soft(),
        css=_CSS,
    ) as app:

        # ── Hero ──────────────────────────────────────────────────────────────
        gr.HTML(
            '<div class="hero">'
            '<div class="hero-title">📄 MarkItDown</div>'
            '<div class="hero-sub">'
            '支持 <b>Word · PDF · PPT · Excel · 图片 · 音频 · 网页 · HTML · Markdown · CSV · EPUB · ZIP · 邮件 · Jupyter</b> 等格式，'
            '可启用自定义 LLM 图片描述或第三方 OCR 插件'
            '</div></div>'
        )

        with gr.Tabs():

            # ═══════════ Tab 1：文件转换 ═══════════════════════════════════
            with gr.Tab("📁 文件转换"):
                with gr.Row(equal_height=False):

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
                                info="将加载已安装的 markitdown 插件（如 markitdown-ocr）",
                            )
                            plugin_status_txt = gr.Textbox(
                                label=None, value="", interactive=False,
                                max_lines=3, elem_classes=["llm-status"],
                            )
                            enable_plugins_cb.change(
                                fn=on_plugin_toggle,
                                inputs=[enable_plugins_cb],
                                outputs=[plugin_status_txt],
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

        # ── Bottom bar ────────────────────────────────────────────────────────
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

    return app
