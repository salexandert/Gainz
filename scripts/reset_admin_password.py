import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from password_reset import reset_local_login  # noqa: E402


def main():
    os.chdir(REPO_ROOT)

    try:
        result = reset_local_login()
    except Exception as exc:
        print(f"Could not reset the Gainz local login: {exc}")
        print("Close Gainz first if the local database is busy, then try again.")
        return 1

    print("Gainz local login reset.")
    print(f"Local login accounts removed: {result.accounts_removed}")
    print("")
    print("Start or reload Gainz and open the login page.")
    print("Gainz will ask you to choose a new local username and password.")
    print("No temporary or default password was created.")
    print("")
    print(
        "This only resets the Gainz browser login. It does not delete, encrypt, or "
        "protect local CSV, XLSX, save, export, or audit packet files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
