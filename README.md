# MarkItDown GUI

基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 的图形化文档转换工具，将多种格式文件一键转换为 Markdown。

**版本**: v1.0.0

## 功能

- **文件转换** — 支持 Word、PDF、PPT、Excel、图片、音频、HTML、CSV、EPUB、ZIP、邮件等
- **批量处理** — 拖放多个文件，逐条转换并合并输出
- **网页抓取** — 输入 URL 批量抓取并转为 Markdown（含 SSRF 防护 + scheme 白名单）
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

> 端口被占用时会自动寻找下一个可用端口，并写入 `current_port.txt`。该文件写在**程序所在目录**（EXE 模式下为 `MarkItDown.exe` 所在目录，源码模式下为 `markitdown_gui.py` 所在目录）；启动时若默认端口被占用会自动换到 7861/7862 等，并同步删除旧的 `current_port.txt`。

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
markitdown_gui.py            # 入口脚本（薄壳，调用 mdgui.app.main）
mdgui/                       # 核心应用包
├── __init__.py              # 日志加固（dictConfig 安全补丁）
├── converter.py             # 文件/URL 转换 + SSRF 防护
├── llm.py                   # LLM 配置构建与连接测试
├── plugins.py               # 插件检测
├── downloader.py            # 下载处理
├── port_utils.py            # 端口工具
├── process_utils.py         # EXE 旧实例管理
├── ui.py                    # CSS + Gradio UI
└── app.py                   # 主入口逻辑
MarkItDown.spec             # PyInstaller 构建配置
_pyinstaller_runtime_hook.py # PyInstaller 运行时钩子（Gradio 兼容）
_internal_patches/          # Gradio 组件补丁
├── component_meta.py
├── generate_hook.py
└── generate_patch.py
tests/
└── test_conversion.py       # 单元测试（32 用例）
requirements.txt
```

## Changelog

### v1.0.0

- **代码重构** — 单文件拆分为 `mdgui/` 包（9 模块），提升可维护性
- **安全加固**
  - URL 抓取增加 SSRF 防护（阻止内网/回环/链路本地/保留 IP）
  - 非 `http`/`https` scheme（`file:`、`data:`、`ftp:` 等）直接拒绝
  - 进程管理改为完整路径匹配，避免误杀无关进程
- **测试补充** — 从 14 个测试扩展到 32 个，覆盖 SSRF、下载、LLM 等核心路径
- **修复** — `generate_patch.py` 模板逻辑损坏问题

## 致谢

本项目基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown)（MIT License）构建，使用 [Gradio](https://www.gradio.app/) 提供图形界面。

## License

MIT — 详见 [LICENSE](LICENSE)
