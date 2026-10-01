import secrets
import smtplib

from datetime import datetime, timedelta
from email.message import EmailMessage

from werkzeug.security import generate_password_hash


def generate_otp():
    """
    Generate a secure 6-digit OTP.
    """

    return f"{secrets.randbelow(1000000):06d}"


def create_otp():
    """
    Generate an OTP and return:
    - plain OTP for sending by email
    - hashed OTP for database storage
    - expiry time
    """

    otp = generate_otp()

    otp_hash = generate_password_hash(
        otp
    )

    expires_at = (
        datetime.utcnow()
        + timedelta(minutes=5)
    )

    return (
        otp,
        otp_hash,
        expires_at
    )


def send_otp_email(
    recipient_email,
    student_name,
    leave_date,
    otp
):
    """
    Send the OTP to the parent's email address.
    """

    from flask import current_app

    sender_email = current_app.config.get(
        "MAIL_USERNAME"
    )

    sender_password = current_app.config.get(
        "MAIL_PASSWORD"
    )

    if not sender_email:
        raise ValueError(
            "MAIL_USERNAME is not configured."
        )

    if not sender_password:
        raise ValueError(
            "MAIL_PASSWORD is not configured."
        )

    message = EmailMessage()

    message["Subject"] = (
        "Campus Outing Approval OTP"
    )

    message["From"] = sender_email

    message["To"] = recipient_email

    message.set_content(
        f"""
Campus Outing Management System

Dear Parent,

A leave application has been submitted for:

Student: {student_name}
Leave Date: {leave_date}

An approval request has been initiated.

Your One-Time Password (OTP) is:

{otp}

This OTP is valid for 5 minutes.

Please enter this OTP in the Campus Outing Management System
to confirm your approval.

If you did not initiate or expect this request, please ignore
this email.

Regards,
Campus Outing Management System
"""
    )

    with smtplib.SMTP(
        current_app.config["MAIL_SERVER"],
        current_app.config["MAIL_PORT"]
    ) as server:

        if current_app.config["MAIL_USE_TLS"]:

            server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        server.send_message(
            message
        )