import os
import socket
import tempfile

import pytest

from mdgui.converter import _convert_single, _is_safe_url, convert_urls
from mdgui.downloader import _show_download_if_content
from mdgui.llm import _build_llm_kwargs, on_test_llm
from mdgui.plugins import _detect_installed_plugins, on_plugin_toggle
from mdgui.port_utils import _find_free_port, _port_is_free


class TestBuildLlmKwargs:
    def test_all_disabled(self):
        kwargs = _build_llm_kwargs(False, "", "", "", "")
        assert kwargs == {}

    def test_enabled_but_missing_url(self):
        kwargs = _build_llm_kwargs(True, "", "key", "gpt-4o", "")
        assert kwargs == {}

    def test_enabled_but_missing_key(self):
        kwargs = _build_llm_kwargs(True, "http://localhost:8000/v1", "", "gpt-4o", "")
        assert kwargs == {}

    def test_enabled_but_missing_model(self):
        kwargs = _build_llm_kwargs(True, "http://localhost:8000/v1", "sk-test", "", "")
        assert kwargs == {}

    def test_enabled_all_provided(self):
        kwargs = _build_llm_kwargs(
            True, "http://localhost:8000/v1", "sk-test", "gpt-4o", "describe this image"
        )
        assert "llm_client" in kwargs
        assert kwargs["llm_model"] == "gpt-4o"
        assert kwargs["llm_prompt"] == "describe this image"

    def test_enabled_no_custom_prompt(self):
        kwargs = _build_llm_kwargs(
            True, "http://localhost:8000/v1", "sk-test", "gpt-4o", ""
        )
        assert "llm_prompt" not in kwargs


class TestPortIsFree:
    def test_port_in_use(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            assert _port_is_free(port) is False
        finally:
            listener.close()

    def test_port_free(self):
        port = _find_free_port(18000, 5)
        assert _port_is_free(port) is True


class TestFindFreePort:
    def test_returns_int_in_range(self):
        port = _find_free_port(18000, 5)
        assert isinstance(port, int)
        assert 18000 <= port < 18005

    def test_returns_start_port_when_free(self):
        free_port = _find_free_port(18000, 5)
        if free_port != 18000:
            pytest.skip("18000 happened to be in use; cannot assert start_port")
        assert free_port == 18000


class TestDetectInstalledPlugins:
    def test_returns_list(self):
        plugins = _detect_installed_plugins()
        assert isinstance(plugins, list)

    def test_names_are_strings(self):
        plugins = _detect_installed_plugins()
        assert all(isinstance(name, str) for name in plugins)


class TestOnPluginToggle:
    def test_unchecked_returns_empty(self):
        assert on_plugin_toggle(False) == ""

    def test_checked_returns_string(self):
        msg = on_plugin_toggle(True)
        assert isinstance(msg, str)


class TestConvertSingle:
    def test_simple_text_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello, World!")
            tmp_path = f.name
        try:
            result, error, elapsed = _convert_single(tmp_path)
            assert error is None
            assert "Hello, World!" in result
            assert elapsed > 0
        finally:
            os.unlink(tmp_path)

    def test_missing_file_returns_error(self):
        result, error, elapsed = _convert_single("/nonexistent/path/file.txt")
        assert error is not None
        assert result == ""
        assert elapsed == 0


class TestShowDownloadIfContent:
    def test_empty_text_hidden(self):
        btn = _show_download_if_content("")
        assert btn.visible is False

    def test_whitespace_only_hidden(self):
        btn = _show_download_if_content("   ")
        assert btn.visible is False

    def test_waiting_text_hidden(self):
        btn = _show_download_if_content("等待上传文件…")
        assert btn.visible is False

    def test_real_content_visible(self):
        btn = _show_download_if_content("# Heading\nSome content")
        assert btn.visible is True


class TestIsSafeUrl:
    def test_public_url_is_safe(self):
        assert _is_safe_url("https://example.com/page") is True

    def test_loopback_blocked(self):
        assert _is_safe_url("http://127.0.0.1:8080/admin") is False

    def test_private_ip_blocked(self):
        assert _is_safe_url("http://192.168.1.1/router") is False

    def test_link_local_blocked(self):
        assert _is_safe_url("http://169.254.0.1/") is False

    def test_unresolvable_hostname_is_safe(self):
        # Unresolvable hostnames pass through; the fetch itself will fail
        assert _is_safe_url("http://definitely-not-a-real-xyz.invalid/") is True

    def test_file_uri_blocked(self):
        assert _is_safe_url("file:///C:/Windows/System32/cmd.exe") is False

    def test_data_uri_blocked(self):
        assert _is_safe_url("data:text/plain;base64,SGVsbG8=") is False

    def test_non_http_scheme_blocked(self):
        assert _is_safe_url("ftp://example.com/file.txt") is False


class TestConvertUrlsGenerator:
    def test_empty_input(self):
        results = list(convert_urls(""))
        assert results[0][0] == "[请输入 URL]"
        assert results[0][2] == "URL 为空"

    def test_none_input(self):
        results = list(convert_urls(None))
        assert results[0][0] == "[请输入 URL]"


class TestOnTestLlm:
    def test_missing_params(self):
        msg = on_test_llm("", "", "")
        assert "❌" in msg
        assert "Base URL" in msg

    def test_invalid_url_returns_error(self):
        msg = on_test_llm("http://invalid.localhost:99999", "sk-x", "gpt-4o")
        assert "❌" in msg
