"""Document / URL conversion with SSRF protection."""
import ipaddress
import os
import socket
import time
from urllib.parse import urlparse

from markitdown import MarkItDown, UnsupportedFormatException, FileConversionException

from .llm import _build_llm_kwargs

md = MarkItDown()


def _resolve_ip(url: str):
    """Resolve hostname to IP.  Returns ipaddress object or None on failure."""
    try:
        host = urlparse(url).hostname
        if not host:
            return None
        # If host is already an IP literal, parse directly
        try:
            return ipaddress.ip_address(host)
        except ValueError:
            pass
        try:
            infos = socket.getaddrinfo(host, None)
            return ipaddress.ip_address(infos[0][4][0])
        except Exception:
            return None
    except Exception:
        return None


def _is_safe_url(url: str) -> bool:
    """Reject URLs that resolve to private / loopback / link-local / reserved IPs."""
    ip = _resolve_ip(url)
    if ip is None:
        return True  # unresolvable → let the fetch itself fail with a clear error
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    )


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
        text, err, elapsed = _convert_single(
            path,
            enable_llm=enable_llm,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            enable_plugins=enable_plugins,
            llm_prompt=llm_prompt,
        )
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
        if not _is_safe_url(url):
            parts.append(f"## ⚠️ {url}\n\n_已阻止：该地址解析为内网 / 保留 IP（SSRF 防护）_\n")
            yield "\n\n".join(parts), "\n\n".join(parts), f"已阻止 ({i}/{len(lines)}): SSRF", f"{total_chars} 字符 · {total_elapsed:.2f}s"
            continue
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
