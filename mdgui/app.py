"""Application entry point: port setup, browser launch, and retry logic."""
import os
import sys
import threading
import time
import traceback
import webbrowser

from .port_utils import _find_free_port
from .process_utils import _kill_old_instances
from .ui import _set_port, _get_port, build_ui


def _project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _log_startup_error(prefix: str, exc: BaseException):
    try:
        err_file = os.path.join(_project_root(), "startup_error.log")
        with open(err_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{prefix}] {type(exc).__name__}: {exc}\n")
            f.write(traceback.format_exc())
    except Exception:
        pass


def _setup_server():
    env_port = os.environ.get("GRADIO_SERVER_PORT")
    if env_port and env_port.isdigit():
        port = int(env_port)
    else:
        port = _find_free_port(7860, 20)
        if port != 7860:
            try:
                port_file = os.path.join(_project_root(), "current_port.txt")
                with open(port_file, "w", encoding="utf-8") as f:
                    f.write(str(port))
            except Exception:
                pass
    _set_port(port)
    return port


def main():
    try:
        _kill_old_instances()
    except BaseException as e:
        _log_startup_error("_kill_old_instances", e)

    port = _setup_server()

    def _open_browser():
        time.sleep(3.0)
        try:
            webbrowser.open(f"http://127.0.0.1:{_get_port()}/", new=1, autoraise=True)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    print(f"MarkItDown GUI 正在启动：http://127.0.0.1:{port}/")
    print("若浏览器未自动打开，请在浏览器中访问上方网址。")

    app = build_ui()

    def _retry_launch(failed_port: int):
        new_port = _find_free_port(failed_port + 1, 10)
        _set_port(new_port)
        app.launch(
            server_name="127.0.0.1",
            server_port=new_port,
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
