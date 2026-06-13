import os
import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from urllib.request import urlopen

from app_version import APP_VERSION
from password_reset import DOCUMENTED_RESET_PHRASE, reset_admin_password
from port_guard import require_port_available
from single_instance import SingleInstanceLock

APP_NAME = "Gainz"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_SUPPORT_URL = "https://cash.app/$SAl3xander"
STARTUP_CHECK_INTERVAL_MS = 500


def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))


def find_available_port(preferred_port=DEFAULT_PORT):
    configured_port = os.environ.get("GAINZ_PORT")
    port = int(configured_port) if configured_port else preferred_port

    require_port_available(DEFAULT_HOST, port)
    return port



def server_url(port):
    return f"http://{DEFAULT_HOST}:{port}"


def health_url(port):
    return f"{server_url(port)}/healthz"


def support_url():
    return os.environ.get("GAINZ_SUPPORT_URL", DEFAULT_SUPPORT_URL)


def wait_for_lock_info(instance_lock, timeout=3):
    deadline = time.time() + timeout
    info = instance_lock.read_info()
    while time.time() < deadline and not (info.get("port") or info.get("url")):
        time.sleep(0.25)
        info = instance_lock.read_info()

    return info


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
        os.environ["GAINZ_HOST"] = DEFAULT_HOST
        os.environ["GAINZ_PORT"] = str(port)

        from run import app

        app.run(host=DEFAULT_HOST, port=port, debug=False, use_reloader=False)
    except Exception as exc:
        error_queue.put(exc)


class GainzLauncher(tk.Tk):
    def __init__(self, instance_lock, port=None):
        super().__init__()
        self.instance_lock = instance_lock
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("560x350")
        self.resizable(False, False)
        self.configure(padx=24, pady=22)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        os.chdir(app_base_dir())
        self.port = port if port is not None else find_available_port()
        self.url = server_url(self.port)
        self.health_url = health_url(self.port)
        self.instance_lock.write_info(port=self.port, url=self.url, status="starting")
        self.support_url = support_url()
        self.error_queue = queue.Queue()
        self.started_at = time.time()
        self.browser_opened = False

        self.status = tk.StringVar(
            value="Starting Gainz local server. This can take a minute while your save loads..."
        )
        self.heading_text = tk.StringVar(value=f"Gainz {APP_VERSION} is starting")
        self.url_text = tk.StringVar(value=self.url)
        self.credentials_text = tk.StringVar(value=self.credentials_message())

        self.build_ui()
        self.start_server_thread()
        self.after(250, self.check_startup)

    def credentials_message(self):
        return "First run: create a local admin account in the browser. No Gainz account data leaves this computer."

    def build_ui(self):
        title = ttk.Label(self, textvariable=self.heading_text, font=("Segoe UI", 16, "bold"))
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
        ttk.Button(button_frame, text="Reset Password", command=self.reset_password).pack(side="left", padx=(8, 0))
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

        elapsed = int(time.time() - self.started_at)
        self.status.set(
            f"Starting Gainz local server... {elapsed}s elapsed. Keep this window open."
        )

        if wait_for_server(self.health_url, timeout=1):
            self.heading_text.set(f"Gainz {APP_VERSION} is running")
            self.status.set("Gainz is running.")
            self.instance_lock.write_info(port=self.port, url=self.url, status="running")
            self.open_button.configure(state="normal")
            self.title(f"{APP_NAME} {APP_VERSION} - Running")
            if not self.browser_opened and os.environ.get("GAINZ_AUTO_OPEN", "1") != "0":
                self.browser_opened = True
                self.after(250, self.open_gainz)
            return

        self.after(STARTUP_CHECK_INTERVAL_MS, self.check_startup)

    def open_gainz(self):
        webbrowser.open(self.url)

    def copy_link(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)
        self.status.set("Link copied. Gainz is running.")

    def open_support(self):
        webbrowser.open(self.support_url)

    def reset_password(self):
        confirmed = messagebox.askyesno(
            APP_NAME,
            "Reset the local admin password to the temporary default?\n\n"
            "This only changes the Gainz browser login. It does not encrypt or "
            "protect local CSV, XLSX, save, export, or audit packet files.",
        )
        if not confirmed:
            return

        try:
            result = reset_admin_password(password=DOCUMENTED_RESET_PHRASE)
        except Exception as exc:
            messagebox.showerror(
                APP_NAME,
                "Gainz could not reset the local password.\n\n"
                f"{exc}\n\n"
                "Close Gainz first if the local database is busy, then try again.",
            )
            return

        action = "created" if result.created else "reset"
        self.credentials_text.set(
            f"Local admin password {action}. Username: {result.username}. "
            "Sign in with the temporary reset password, then change it from the gear menu."
        )
        messagebox.showinfo(
            APP_NAME,
            f"Gainz local admin password {action}.\n\n"
            f"Username: {result.username}\n"
            f"Temporary password: {DOCUMENTED_RESET_PHRASE}\n\n"
            "Sign in locally, then use the gear menu > Change Password.",
        )

    def close_app(self):
        self.instance_lock.release()
        self.destroy()
        os._exit(0)


def main():
    os.chdir(app_base_dir())
    instance_lock = SingleInstanceLock(app_base_dir())
    if not instance_lock.acquire():
        info = wait_for_lock_info(instance_lock)
        port = int(info.get("port") or DEFAULT_PORT)
        url = info.get("url") or server_url(port)
        root = tk.Tk()
        root.withdraw()

        if wait_for_server(health_url(port), timeout=5):
            webbrowser.open(url)
            messagebox.showinfo(
                APP_NAME,
                f"Gainz is already running.\n\nOpening the existing app at:\n{url}",
            )
        else:
            messagebox.showwarning(
                APP_NAME,
                "Gainz is already starting or another Gainz process is holding the app lock. "
                "Wait a moment, then use the existing Gainz window or try again.",
            )
        root.destroy()
        return

    try:
        port = find_available_port()
    except RuntimeError as exc:
        instance_lock.release()
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, str(exc))
        root.destroy()
        return

    launcher = GainzLauncher(instance_lock, port=port)
    launcher.mainloop()


if __name__ == "__main__":
    main()
