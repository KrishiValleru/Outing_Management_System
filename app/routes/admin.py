from datetime import date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from ..extensions import db
from ..models import PermittedDate


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


@admin_bp.route("/")
@login_required
def dashboard():

    if current_user.role != "admin":
        return "Unauthorized", 403

    permitted_dates = PermittedDate.query.order_by(
        PermittedDate.leave_date.asc()
    ).all()

    return render_template(
        "admin/dashboard.html",
        permitted_dates=permitted_dates
    )


@admin_bp.route(
    "/dates",
    methods=["GET", "POST"]
)
@login_required
def permitted_dates():

    if current_user.role != "admin":
        return "Unauthorized", 403

    if request.method == "POST":

        date_string = request.form.get(
            "leave_date"
        )

        description = request.form.get(
            "description"
        )

        if not date_string:

            flash(
                "Please select a date.",
                "error"
            )

            return redirect(
                url_for("admin.permitted_dates")
            )

        try:

            selected_date = date.fromisoformat(
                date_string
            )

        except ValueError:

            flash(
                "Invalid date.",
                "error"
            )

            return redirect(
                url_for("admin.permitted_dates")
            )

        existing_date = PermittedDate.query.filter_by(
            leave_date=selected_date
        ).first()

        if existing_date:

            flash(
                "This date is already permitted.",
                "error"
            )

            return redirect(
                url_for("admin.permitted_dates")
            )

        permitted_date = PermittedDate(
            leave_date=selected_date,
            description=description
        )

        db.session.add(
            permitted_date
        )

        db.session.commit()

        flash(
            "Permitted outing date added successfully.",
            "success"
        )

        return redirect(
            url_for("admin.permitted_dates")
        )

    dates = PermittedDate.query.order_by(
        PermittedDate.leave_date.asc()
    ).all()

    return render_template(
        "admin/holidays.html",
        permitted_dates=dates
    )


@admin_bp.route(
    "/dates/delete/<int:date_id>",
    methods=["POST"]
)
@login_required
def delete_permitted_date(date_id):

    if current_user.role != "admin":
        return "Unauthorized", 403

    permitted_date = PermittedDate.query.get_or_404(
        date_id
    )

    db.session.delete(
        permitted_date
    )

    db.session.commit()

    flash(
        "Permitted outing date removed.",
        "success"
    )

    return redirect(
        url_for("admin.permitted_dates")
    )