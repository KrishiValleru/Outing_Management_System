import os


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-key"
    )

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///outing.db"
    )

    # Render/PostgreSQL may provide postgres://
    # SQLAlchemy expects postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv(
        "MAIL_SERVER",
        "smtp.gmail.com"
    )

    MAIL_PORT = int(
        os.getenv(
            "MAIL_PORT",
            "587"
        )
    )

    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME"
    )

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD"
    )

    MAIL_USE_TLS = os.getenv(
        "MAIL_USE_TLS",
        "True"
    ).lower() == "true"