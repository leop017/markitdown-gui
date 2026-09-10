import os
import socket
import tempfile

import pytest

import markitdown_gui as gui


class TestBuildLlmKwargs:
    def test_all_disabled(self):
        kwargs = gui._build_llm_kwargs(False, "", "", "", "")
        assert kwargs == {}

    def test_enabled_but_missing_url(self):
        kwargs = gui._build_llm_kwargs(True, "", "key", "gpt-4o", "")
        assert kwargs == {}

    def test_enabled_but_missing_key(self):
        kwargs = gui._build_llm_kwargs(True, "http://localhost:8000/v1", "", "gpt-4o", "")
        assert kwargs == {}

    def test_enabled_but_missing_model(self):
        kwargs = gui._build_llm_kwargs(True, "http://localhost:8000/v1", "sk-test", "", "")
        assert kwargs == {}

    def test_enabled_all_provided(self):
        kwargs = gui._build_llm_kwargs(
            True, "http://localhost:8000/v1", "sk-test", "gpt-4o", "describe this image"
        )
        assert "llm_client" in kwargs
        assert kwargs["llm_model"] == "gpt-4o"
        assert kwargs["llm_prompt"] == "describe this image"

    def test_enabled_no_custom_prompt(self):
        kwargs = gui._build_llm_kwargs(
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
            assert gui._port_is_free(port) is False
        finally:
            listener.close()

    def test_port_free(self):
        port = gui._find_free_port(18000, 5)
        assert gui._port_is_free(port) is True


class TestFindFreePort:
    def test_returns_int_in_range(self):
        port = gui._find_free_port(18000, 5)
        assert isinstance(port, int)
        assert 18000 <= port < 18005

    def test_returns_start_port_when_free(self):
        free_port = gui._find_free_port(18000, 5)
        if free_port != 18000:
            pytest.skip("18000 happened to be in use; cannot assert start_port")
        assert free_port == 18000


class TestDetectInstalledPlugins:
    def test_returns_list(self):
        plugins = gui._detect_installed_plugins()
        assert isinstance(plugins, list)

    def test_names_are_strings(self):
        plugins = gui._detect_installed_plugins()
        assert all(isinstance(name, str) for name in plugins)


class TestOnPluginToggle:
    def test_unchecked_returns_empty(self):
        assert gui.on_plugin_toggle(False) == ""

    def test_checked_returns_string(self):
        msg = gui.on_plugin_toggle(True)
        assert isinstance(msg, str)


class TestConvertSingle:
    def test_simple_text_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello, World!")
            tmp_path = f.name
        try:
            result, error, elapsed = gui._convert_single(tmp_path)
            assert error is None
            assert "Hello, World!" in result
            assert elapsed > 0
        finally:
            os.unlink(tmp_path)

    def test_missing_file_returns_error(self):
        result, error, elapsed = gui._convert_single("/nonexistent/path/file.txt")
        assert error is not None
        assert result == ""
        assert elapsed == 0
