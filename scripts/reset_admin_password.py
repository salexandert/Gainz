import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from password_reset import DOCUMENTED_RESET_PHRASE, reset_admin_password  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Reset the local Gainz admin password."
    )
    parser.add_argument(
        "--password",
        default=DOCUMENTED_RESET_PHRASE,
        help="Temporary password to set. Defaults to the documented local reset password.",
    )
    args = parser.parse_args()

    os.chdir(REPO_ROOT)

    try:
        result = reset_admin_password(password=args.password)
    except Exception as exc:
        print(f"Could not reset the Gainz password: {exc}")
        print("Close Gainz first if the local database is busy, then try again.")
        return 1

    action = "created" if result.created else "reset"
    print(f"Gainz local admin password {action}.")
    print(f"Username: {result.username}")
    if args.password == DOCUMENTED_RESET_PHRASE:
        print("Temporary password set to the documented local reset password.")
    else:
        print("Temporary password set to the value provided on the command line.")
    print("")
    print("Sign in locally, then use the gear menu > Change Password.")
    print(
        "This only changes the Gainz browser login. It does not encrypt or "
        "protect local CSV, XLSX, save, export, or audit packet files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
