import socket


def port_is_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, int(port)))
        except OSError:
            return False

    return True


def require_port_available(host, port):
    if port_is_available(host, port):
        return

    raise RuntimeError(
        f"Port {port} is already in use on {host}. "
        "Close the other app or existing Gainz window before starting Gainz."
    )
