from flask import Flask
from dotenv import load_dotenv


def create_app():

    # Load environment variables BEFORE
    # importing the Config class.
    load_dotenv()

    from .config import Config
    from .extensions import db, login_manager

    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)

    login_manager.init_app(app)

    from .models import User

    from .routes.auth import auth_bp
    from .routes.student import student_bp
    from .routes.parent import parent_bp
    from .routes.admin import admin_bp
    from .routes.gate import gate_bp

    app.register_blueprint(auth_bp)

    app.register_blueprint(student_bp)

    app.register_blueprint(parent_bp)

    app.register_blueprint(admin_bp)

    app.register_blueprint(gate_bp)

    with app.app_context():

        db.create_all()

    return app


from .extensions import login_manager


@login_manager.user_loader
def load_user(user_id):

    from .models import User

    return User.query.get(
        int(user_id)
    )