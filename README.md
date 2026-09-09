# MarkItDown GUI

基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 的图形化文档转换工具，将多种格式文件一键转换为 Markdown。

## 功能

- **文件转换** — 支持 Word、PDF、PPT、Excel、图片、音频、HTML、CSV、EPUB、ZIP、邮件等
- **批量处理** — 拖放多个文件，逐条转换并合并输出
- **网页抓取** — 输入 URL 批量抓取并转为 Markdown
- **LLM 图片描述** — 配置任意 OpenAI 兼容接口，自动为图片生成描述
- **第三方插件** — 支持 markitdown-ocr 等 OCR 插件
- **一键下载** — 转换结果保存为 `.md` 文件

## 环境要求

- Windows x64
- Python 3.10+

## 安装与运行

```powershell
# 克隆仓库
git clone https://github.com/leop017/markitdown-gui.git
cd markitdown-gui

# 安装依赖
pip install -r requirements.txt

# 启动
python markitdown_gui.py
```

启动后浏览器自动打开 `http://127.0.0.1:7860/`。

> 端口被占用时会自动寻找下一个可用端口，并写入 `current_port.txt`。

## 构建 EXE

```powershell
pip install pyinstaller
pyinstaller MarkItDown.spec
```

生成的单文件 EXE 位于 `dist/MarkItDown.exe`，双击即可运行，无需 Python 环境。

## LLM 配置

在 GUI 中展开 **「⚙️ 转换选项 → 🔗 LLM 连接配置」**：

| 字段 | 说明 | 示例 |
|------|------|------|
| 接口地址（Base URL） | OpenAI 兼容接口地址 | `https://api.openai.com/v1` |
| 密钥（API Key） | 密钥 | `sk-...` |
| 模型名称 | 模型标识 | `gpt-4o`、`deepseek-v3` |
| 自定义 Prompt（可选） | 图片描述提示词，留空使用默认 | `请用中文描述这张图片` |

支持 vLLM、硅基流动、LocalAI、Ollama 等所有 OpenAI 兼容服务。

## 项目结构

```
markitdown_gui.py            # GUI 主程序
MarkItDown.spec             # PyInstaller 构建配置
_pyinstaller_runtime_hook.py # PyInstaller 运行时钩子（Gradio 兼容）
_internal_patches/          # Gradio 组件补丁
├── component_meta.py
├── generate_hook.py
└── generate_patch.py
requirements.txt
```

## 致谢

本项目基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown)（MIT License）构建，使用 [Gradio](https://www.gradio.app/) 提供图形界面。

## License

MIT — 详见 [LICENSE](LICENSE)
