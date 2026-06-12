import json
import os
import time

try:
    import msvcrt
except ImportError:  # pragma: no cover - exercised on non-Windows platforms
    msvcrt = None

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None


LOCK_FILENAME = "gainz.lock"


class SingleInstanceLock:
    def __init__(self, base_dir):
        instance_dir = os.path.join(base_dir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        self.path = os.path.join(instance_dir, LOCK_FILENAME)
        self._handle = None
        self.acquired = False

    def acquire(self):
        if self.acquired:
            return True

        self._handle = open(self.path, "a+", encoding="utf-8")
        self._handle.seek(0, os.SEEK_END)
        if self._handle.tell() == 0:
            self._handle.write(" ")
            self._handle.flush()
            os.fsync(self._handle.fileno())
        self._handle.seek(0)

        try:
            if msvcrt:
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            elif fcntl:
                fcntl.lockf(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise RuntimeError("No supported file locking backend is available.")
        except (OSError, RuntimeError):
            self._handle.close()
            self._handle = None
            self.acquired = False
            return False

        self.acquired = True
        self.write_info(status="starting")
        return True

    def write_info(self, **info):
        if not self.acquired or not self._handle:
            return

        current = self.read_info()
        current.update(
            {
                "pid": os.getpid(),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                **info,
            }
        )
        self._handle.seek(1)
        self._handle.truncate()
        json.dump(current, self._handle, indent=2, sort_keys=True)
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self._handle.seek(0)

    def read_info(self):
        return read_lock_info(self.path)

    def release(self):
        if not self._handle:
            return

        try:
            self._handle.seek(0)
            if msvcrt:
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            elif fcntl:
                fcntl.lockf(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Gainz is already running.")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.release()


def read_lock_info(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            handle.seek(1)
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
