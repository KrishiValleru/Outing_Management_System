from datetime import date
import base64
import io
import secrets

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

from ..models import (
    LeaveApplication,
    PermittedDate
)


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student"
)


@student_bp.route("/")
@login_required
def dashboard():

    applications = LeaveApplication.query.filter_by(
        student_id=current_user.id
    ).order_by(
        LeaveApplication.leave_date.desc()
    ).all()

    permitted_dates = PermittedDate.query.filter(
        PermittedDate.leave_date >= date.today()
    ).order_by(
        PermittedDate.leave_date.asc()
    ).all()

    return render_template(
        "student/dashboard.html",
        applications=applications,
        permitted_dates=permitted_dates
    )


@student_bp.route(
    "/apply-leave",
    methods=["GET", "POST"]
)
@login_required
def apply_leave():

    if request.method == "POST":

        leave_date_string = request.form.get(
            "leave_date"
        )

        leave_type = request.form.get(
            "leave_type"
        )

        reason = request.form.get(
            "reason"
        )

        if (
            not leave_date_string
            or not leave_type
            or not reason
        ):

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("student.apply_leave")
            )

        if leave_type not in [
            "regular",
            "emergency"
        ]:

            flash(
                "Invalid leave type.",
                "error"
            )

            return redirect(
                url_for("student.apply_leave")
            )

        try:

            leave_date = date.fromisoformat(
                leave_date_string
            )

        except ValueError:

            flash(
                "Invalid date.",
                "error"
            )

            return redirect(
                url_for("student.apply_leave")
            )

        if leave_date < date.today():

            flash(
                "You cannot apply for a past date.",
                "error"
            )

            return redirect(
                url_for("student.apply_leave")
            )

        # Regular leave must be on an
        # administrator-permitted date.
        if leave_type == "regular":

            permitted_date = PermittedDate.query.filter_by(
                leave_date=leave_date
            ).first()

            if not permitted_date:

                flash(
                    "Regular leave is not permitted "
                    "on this date. Please select a "
                    "date from the campus leave calendar.",
                    "error"
                )

                return redirect(
                    url_for("student.apply_leave")
                )

        # Prevent duplicate applications
        # for the same student and date.
        existing_application = LeaveApplication.query.filter_by(
            student_id=current_user.id,
            leave_date=leave_date
        ).first()

        if existing_application:

            flash(
                "You already have a leave application "
                "for this date.",
                "error"
            )

            return redirect(
                url_for("student.apply_leave")
            )

        application = LeaveApplication(
            student_id=current_user.id,
            leave_date=leave_date,
            leave_type=leave_type,
            reason=reason,
            status="pending"
        )

        db.session.add(
            application
        )

        db.session.commit()

        flash(
            "Leave application submitted successfully.",
            "success"
        )

        return redirect(
            url_for("student.dashboard")
        )

    permitted_dates = PermittedDate.query.filter(
        PermittedDate.leave_date >= date.today()
    ).order_by(
        PermittedDate.leave_date.asc()
    ).all()

    permitted_date_strings = [
        permitted_date.leave_date.isoformat()
        for permitted_date in permitted_dates
    ]

    return render_template(
        "student/apply_leave.html",
        today=date.today().isoformat(),
        permitted_dates=permitted_date_strings
    )


@student_bp.route(
    "/qr/<int:application_id>"
)
@login_required
def qr_code(application_id):

    application = LeaveApplication.query.get_or_404(
        application_id
    )

    if application.student_id != current_user.id:

        return "Unauthorized", 403

    if application.status != "approved":

        flash(
            "This leave application has not been approved.",
            "error"
        )

        return redirect(
            url_for("student.dashboard")
        )

    if not application.qr_token:

        application.qr_token = secrets.token_urlsafe(
            32
        )

        application.qr_used = False

        db.session.commit()

    from ..services.qr_service import generate_qr_image

    qr_image = generate_qr_image(
        application.qr_token
    )

    image_stream = io.BytesIO()

    qr_image.save(
        image_stream,
        format="PNG"
    )

    image_stream.seek(0)

    qr_base64 = base64.b64encode(
        image_stream.getvalue()
    ).decode("utf-8")

    return render_template(
        "student/qr.html",
        application=application,
        qr_base64=qr_base64
    )