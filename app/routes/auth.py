from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_user,
    logout_user,
    current_user
)

from ..models import User


auth_bp = Blueprint(
    "auth",
    __name__
)


@auth_bp.route("/", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for(
                f"{current_user.role}.dashboard"
            )
        )

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        user = User.query.filter_by(
            email=email,
            role=role
        ).first()

        if user and user.check_password(password):

            login_user(user)

            return redirect(
                url_for(
                    f"{user.role}.dashboard"
                )
            )

        flash(
            "Invalid email, password, or role.",
            "error"
        )

    return render_template(
        "auth/login.html"
    )


@auth_bp.route("/logout")
def logout():

    logout_user()

    return redirect(
        url_for("auth.login")
    )