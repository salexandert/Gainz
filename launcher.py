import os
import queue
import socket
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from urllib.request import urlopen


APP_NAME = "Gainz"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_SUPPORT_URL = "https://cash.app/$SAl3xander"


def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))


def find_available_port(preferred_port=DEFAULT_PORT):
    configured_port = os.environ.get("GAINZ_PORT")
    if configured_port:
        return int(configured_port)

    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((DEFAULT_HOST, port)) != 0:
                return port

    raise RuntimeError("No local port is available for Gainz.")


def server_url(port):
    return f"http://{DEFAULT_HOST}:{port}"


def support_url():
    return os.environ.get("GAINZ_SUPPORT_URL", DEFAULT_SUPPORT_URL)


def wait_for_server(url, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.25)

    return False


def start_gainz_server(port, error_queue):
    try:
        from run import app

        app.run(host=DEFAULT_HOST, port=port, debug=False, use_reloader=False)
    except Exception as exc:
        error_queue.put(exc)


class GainzLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("520x320")
        self.resizable(False, False)
        self.configure(padx=24, pady=22)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        os.chdir(app_base_dir())
        self.port = find_available_port()
        self.url = server_url(self.port)
        self.support_url = support_url()
        self.error_queue = queue.Queue()

        self.status = tk.StringVar(value="Starting Gainz...")
        self.url_text = tk.StringVar(value=self.url)
        self.credentials_text = tk.StringVar(value=self.credentials_message())

        self.build_ui()
        self.start_server_thread()
        self.after(250, self.check_startup)

    def credentials_message(self):
        credentials_path = os.path.join(app_base_dir(), "instance", "first_run_credentials.txt")
        return f"First-run credentials, when needed, are saved at:\n{credentials_path}"

    def build_ui(self):
        title = ttk.Label(self, text="Gainz is starting", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        description = ttk.Label(
            self,
            text="Keep this window open while using Gainz. Your data stays on this computer.",
            wraplength=460,
        )
        description.pack(anchor="w", pady=(8, 14))

        self.status_label = ttk.Label(self, textvariable=self.status, font=("Segoe UI", 10, "bold"))
        self.status_label.pack(anchor="w")

        url_frame = ttk.Frame(self)
        url_frame.pack(fill="x", pady=(12, 4))
        ttk.Label(url_frame, text="Web interface:").pack(anchor="w")
        url_value = ttk.Entry(url_frame, textvariable=self.url_text)
        url_value.pack(fill="x", pady=(4, 0))

        credentials = ttk.Label(self, textvariable=self.credentials_text, wraplength=460)
        credentials.pack(anchor="w", pady=(12, 0))

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", side="bottom", pady=(18, 0))

        self.open_button = ttk.Button(button_frame, text="Open Gainz", command=self.open_gainz, state="disabled")
        self.open_button.pack(side="left")

        ttk.Button(button_frame, text="Copy Link", command=self.copy_link).pack(side="left", padx=(8, 0))
        ttk.Button(button_frame, text="Donate", command=self.open_support).pack(side="left", padx=(8, 0))
        ttk.Button(button_frame, text="Quit", command=self.close_app).pack(side="right")

    def start_server_thread(self):
        self.server_thread = threading.Thread(
            target=start_gainz_server,
            args=(self.port, self.error_queue),
            daemon=True,
        )
        self.server_thread.start()

    def check_startup(self):
        if not self.error_queue.empty():
            exc = self.error_queue.get()
            self.status.set("Gainz could not start.")
            messagebox.showerror(APP_NAME, f"Gainz could not start:\n\n{exc}")
            self.open_button.configure(state="disabled")
            return

        if wait_for_server(self.url, timeout=1):
            self.status.set("Gainz is running.")
            self.open_button.configure(state="normal")
            self.title(f"{APP_NAME} - Running")
            return

        self.after(500, self.check_startup)

    def open_gainz(self):
        webbrowser.open(self.url)

    def copy_link(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)
        self.status.set("Link copied. Gainz is running.")

    def open_support(self):
        webbrowser.open(self.support_url)

    def close_app(self):
        self.destroy()
        os._exit(0)


def main():
    launcher = GainzLauncher()
    launcher.mainloop()


if __name__ == "__main__":
    main()
