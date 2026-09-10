"""Port availability utilities."""
import socket


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
