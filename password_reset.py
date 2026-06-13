from dataclasses import dataclass
from typing import Type


DOCUMENTED_RESET_PHRASE = "gainz-local-reset"
DEFAULT_CONFIG_MODE = "Debug"


@dataclass
class PasswordResetResult:
    username: str
    email: str
    created: bool


def get_config_class(config_mode=None):
    from configs.config import config_dict

    mode = (config_mode or DEFAULT_CONFIG_MODE).capitalize()
    try:
        return config_dict[mode]
    except KeyError as exc:
        raise ValueError(f"Unknown Gainz config mode: {config_mode}") from exc


def reset_admin_password(password=DOCUMENTED_RESET_PHRASE, config_class: Type = None):
    if not password or len(password) < 8:
        raise ValueError("The reset password must be at least 8 characters.")

    from app import create_app, db
    from app.base.models import User

    app = create_app(config_class or get_config_class())

    with app.app_context():
        db.create_all()

        admin_config = dict(app.config["ADMIN"])
        username = admin_config.get("username") or "admin"
        email = admin_config.get("email") or "admin@local.gainz"

        user = User.query.filter_by(username=username).first()
        created = user is None

        if created:
            user = User(username=username, email=email, password=password)
            db.session.add(user)
        else:
            if not user.email:
                user.email = email
            user.password = user.hashpw(password)

        db.session.commit()
        result = PasswordResetResult(
            username=user.username,
            email=user.email,
            created=created,
        )
        db.session.remove()
        db.engine.dispose()

    return result
