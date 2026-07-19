from dataclasses import dataclass
from typing import Type

from local_login import (
    clear_login_setup_requirement,
    login_setup_required,
    require_login_setup,
)

DEFAULT_CONFIG_MODE = "Debug"


@dataclass
class LoginResetResult:
    accounts_removed: int


def get_config_class(config_mode=None):
    from configs.config import config_dict

    mode = (config_mode or DEFAULT_CONFIG_MODE).capitalize()
    try:
        return config_dict[mode]
    except KeyError as exc:
        raise ValueError(f"Unknown Gainz config mode: {config_mode}") from exc


def reset_local_login(config_class: Type = None):
    from app import create_app, db
    from app.base.models import User

    app = create_app(config_class or get_config_class())

    with app.app_context():
        db.create_all()

        instance_path = app.config["INSTANCE_PATH"]
        marker_existed = login_setup_required(instance_path)
        require_login_setup(instance_path)

        try:
            accounts_removed = User.query.delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            if not marker_existed:
                clear_login_setup_requirement(instance_path)
            raise
        finally:
            db.session.remove()
            db.engine.dispose()

    return LoginResetResult(accounts_removed=accounts_removed)
