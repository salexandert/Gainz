from pathlib import Path


LOGIN_SETUP_MARKER = "login_setup_required"


def login_setup_marker_path(instance_path):
    return Path(instance_path) / LOGIN_SETUP_MARKER


def login_setup_required(instance_path):
    return login_setup_marker_path(instance_path).is_file()


def require_login_setup(instance_path):
    marker_path = login_setup_marker_path(instance_path)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        "Gainz will ask for a new local username and password at the next login.\n",
        encoding="utf-8",
    )
    return marker_path


def clear_login_setup_requirement(instance_path):
    login_setup_marker_path(instance_path).unlink(missing_ok=True)
