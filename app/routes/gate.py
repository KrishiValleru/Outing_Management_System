from datetime import date

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify
)

from ..extensions import db
from ..models import LeaveApplication


gate_bp = Blueprint(
    "gate",
    __name__,
    url_prefix="/gate"
)


@gate_bp.route("/")
def scanner():

    return render_template(
        "gate/scanner.html"
    )


@gate_bp.route(
    "/verify",
    methods=["POST"]
)
def verify_qr():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "No QR data received."
        }), 400

    token = data.get("token")

    if not token:

        return jsonify({
            "success": False,
            "message": "QR code does not contain a valid token."
        }), 400

    application = LeaveApplication.query.filter_by(
        qr_token=token
    ).first()

    if not application:

        return jsonify({
            "success": False,
            "message": "Invalid QR code."
        }), 404

    # The leave must have been approved by the parent.
    if application.status != "approved":

        return jsonify({
            "success": False,
            "message": "This leave application is not approved."
        }), 403

    # Prevent the same QR code from being used twice.
    if application.qr_used:

        return jsonify({
            "success": False,
            "message": "This QR code has already been used."
        }), 403

    # The QR is valid only on the approved leave date.
    if application.leave_date != date.today():

        return jsonify({
            "success": False,
            "message": (
                f"This QR code is valid only on "
                f"{application.leave_date}."
            )
        }), 403

    # Mark the QR as used.
    application.qr_used = True

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "QR code verified successfully.",
        "student": application.student.name,
        "date": str(application.leave_date),
        "leave_type": application.leave_type
    })