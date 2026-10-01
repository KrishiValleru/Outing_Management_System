from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from .extensions import db


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    parent = db.relationship(
        "User",
        remote_side=[id],
        backref="children"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"


class LeaveApplication(db.Model):

    __tablename__ = "leave_applications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    leave_date = db.Column(
        db.Date,
        nullable=False
    )

    leave_type = db.Column(
        db.String(20),
        nullable=False
    )

    reason = db.Column(
        db.Text,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    parent_comment = db.Column(
        db.Text,
        nullable=True
    )

    # OTP fields
    otp_hash = db.Column(
        db.String(255),
        nullable=True
    )

    otp_expires_at = db.Column(
        db.DateTime,
        nullable=True
    )

    otp_attempts = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    qr_token = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    qr_used = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    student = db.relationship(
        "User",
        backref="leave_applications"
    )

    def __repr__(self):
        return (
            f"<LeaveApplication "
            f"{self.student_id} "
            f"{self.leave_date} "
            f"{self.status}>"
        )


class PermittedDate(db.Model):

    __tablename__ = "permitted_dates"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    leave_date = db.Column(
        db.Date,
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return (
            f"<PermittedDate "
            f"{self.leave_date}>"
        )