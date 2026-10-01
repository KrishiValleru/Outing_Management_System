from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    flash
)

from flask_login import login_required, current_user
from werkzeug.security import check_password_hash

from ..extensions import db
from ..models import LeaveApplication
from ..services.otp_service import (
    create_otp,
    send_otp_email
)

import secrets


parent_bp = Blueprint(
    "parent",
    __name__,
    url_prefix="/parent"
)


@parent_bp.route("/")
@login_required
def dashboard():

    applications = LeaveApplication.query.join(
        LeaveApplication.student
    ).filter(
        LeaveApplication.student.has(
            parent_id=current_user.id
        )
    ).order_by(
        LeaveApplication.leave_date.desc()
    ).all()

    return render_template(
        "parent/dashboard.html",
        applications=applications
    )


@parent_bp.route(
    "/application/<int:application_id>",
    methods=["GET", "POST"]
)
@login_required
def application(application_id):

    application = LeaveApplication.query.get_or_404(
        application_id
    )

    if application.student.parent_id != current_user.id:
        abort(403)

    if request.method == "POST":

        decision = request.form.get("decision")

        parent_comment = request.form.get(
            "parent_comment"
        )

        if decision not in [
            "approved",
            "declined"
        ]:
            abort(400)

        # -------------------------------------------------
        # DECLINE
        # -------------------------------------------------

        if decision == "declined":

            application.status = "declined"

            application.parent_comment = parent_comment

            application.otp_hash = None

            application.otp_expires_at = None

            application.otp_attempts = 0

            application.qr_token = None

            application.qr_used = False

            db.session.commit()

            flash(
                "Leave application declined.",
                "success"
            )

            return redirect(
                url_for("parent.dashboard")
            )


        # -------------------------------------------------
        # APPROVAL
        # -------------------------------------------------

        if application.status == "approved":

            flash(
                "This application has already been approved.",
                "error"
            )

            return redirect(
                url_for("parent.dashboard")
            )

        # Generate OTP
        otp, otp_hash, expires_at = create_otp()

        application.status = "otp_pending"

        application.parent_comment = parent_comment

        application.otp_hash = otp_hash

        application.otp_expires_at = expires_at

        application.otp_attempts = 0

        # QR must NOT exist before OTP verification
        application.qr_token = None

        application.qr_used = False

        db.session.commit()

        try:

            send_otp_email(
                recipient_email=current_user.email,
                student_name=application.student.name,
                leave_date=application.leave_date,
                otp=otp
            )

        except Exception:

            # If the email fails, don't leave the
            # application stuck waiting for an OTP.

            application.status = "pending"

            application.otp_hash = None

            application.otp_expires_at = None

            application.otp_attempts = 0

            db.session.commit()

            flash(
                "Unable to send the OTP email. "
                "Please try again.",
                "error"
            )

            return redirect(
                url_for(
                    "parent.application",
                    application_id=application.id
                )
            )

        flash(
            "An OTP has been sent to your registered email address.",
            "success"
        )

        return redirect(
            url_for(
                "parent.verify_otp",
                application_id=application.id
            )
        )

    return render_template(
        "parent/application.html",
        application=application
    )


@parent_bp.route(
    "/application/<int:application_id>/verify-otp",
    methods=["GET", "POST"]
)
@login_required
def verify_otp(application_id):

    application = LeaveApplication.query.get_or_404(
        application_id
    )

    if application.student.parent_id != current_user.id:
        abort(403)

    if application.status != "otp_pending":

        flash(
            "This application is not waiting for OTP verification.",
            "error"
        )

        return redirect(
            url_for("parent.dashboard")
        )

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp",
            ""
        ).strip()

        if not entered_otp.isdigit() or len(entered_otp) != 6:

            flash(
                "Please enter the 6-digit OTP.",
                "error"
            )

            return redirect(
                url_for(
                    "parent.verify_otp",
                    application_id=application.id
                )
            )

        # Check expiry
        if (
            not application.otp_expires_at
            or datetime.utcnow()
            > application.otp_expires_at
        ):

            application.otp_hash = None

            application.otp_expires_at = None

            application.otp_attempts = 0

            application.status = "pending"

            db.session.commit()

            flash(
                "The OTP has expired. "
                "Please start the approval process again.",
                "error"
            )

            return redirect(
                url_for(
                    "parent.application",
                    application_id=application.id
                )
            )

        # Limit incorrect attempts
        if application.otp_attempts >= 5:

            application.otp_hash = None

            application.otp_expires_at = None

            application.otp_attempts = 0

            application.status = "pending"

            db.session.commit()

            flash(
                "Too many incorrect OTP attempts. "
                "Please start the approval process again.",
                "error"
            )

            return redirect(
                url_for(
                    "parent.application",
                    application_id=application.id
                )
            )

        # Check OTP
        if not check_password_hash(
            application.otp_hash,
            entered_otp
        ):

            application.otp_attempts += 1

            db.session.commit()

            remaining_attempts = (
                5 - application.otp_attempts
            )

            flash(
                f"Incorrect OTP. "
                f"{remaining_attempts} attempt(s) remaining.",
                "error"
            )

            return redirect(
                url_for(
                    "parent.verify_otp",
                    application_id=application.id
                )
            )

        # -------------------------------------------------
        # OTP CORRECT
        # -------------------------------------------------

        application.status = "approved"

        application.otp_hash = None

        application.otp_expires_at = None

        application.otp_attempts = 0

        application.qr_token = secrets.token_urlsafe(
            32
        )

        application.qr_used = False

        db.session.commit()

        flash(
            "OTP verified. Leave application approved successfully.",
            "success"
        )

        return redirect(
            url_for("parent.dashboard")
        )

    return render_template(
        "parent/verify_otp.html",
        application=application
    )