import os
import sys
import io
import secrets
from datetime import date, datetime

# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# =========================================================
# IMPORTS
# =========================================================

import streamlit as st


# =========================================================
# STREAMLIT CLOUD SECRETS
# =========================================================
# Streamlit Cloud stores deployment configuration in st.secrets.
# The existing Flask configuration reads these values from
# environment variables, so copy the relevant secrets into
# os.environ before create_app() is imported and initialized.

try:
    for key in (
        "DATABASE_URL",
        "SECRET_KEY",
        "MAIL_SERVER",
        "MAIL_PORT",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_USE_TLS",
    ):
        if key in st.secrets and key not in os.environ:
            os.environ[key] = str(st.secrets[key])
except Exception:
    # Local development can continue to use .env.
    pass


from werkzeug.security import check_password_hash
from sqlalchemy.orm import joinedload

from app import create_app
from app.extensions import db
from app.models import (
    User,
    LeaveApplication,
    PermittedDate
)
from app.services.otp_service import (
    create_otp,
    send_otp_email
)
from app.services.qr_service import (
    generate_qr_image
)


# =========================================================
# STREAMLIT CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Campus Outing Management System",
    page_icon="🎓",
    layout="wide"
)


# =========================================================
# FLASK APPLICATION
# =========================================================

@st.cache_resource
def get_flask_app():
    return create_app()


flask_app = get_flask_app()


# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_user(email, password, role):

    with flask_app.app_context():

        user = User.query.filter_by(
            email=email.strip().lower(),
            role=role
        ).first()

        if user and user.check_password(password):

            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "parent_id": user.parent_id
            }

    return None


def get_student_applications(student_id):

    with flask_app.app_context():

        return (
            LeaveApplication.query
            .options(joinedload(LeaveApplication.student))
            .filter(
                LeaveApplication.student_id == student_id
            )
            .order_by(
                LeaveApplication.leave_date.desc()
            )
            .all()
        )


def get_permitted_dates():

    with flask_app.app_context():

        return PermittedDate.query.filter(
            PermittedDate.leave_date >= date.today()
        ).order_by(
            PermittedDate.leave_date.asc()
        ).all()


# =========================================================
# LOGOUT
# =========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "Dashboard"

    st.rerun()


# =========================================================
# LOGIN PAGE
# =========================================================

def login_page():

    st.title(
        "Campus Outing Management System"
    )

    st.subheader(
        "Login"
    )

    with st.form("login_form"):

        role = st.selectbox(
            "Login as",
            [
                "student",
                "parent",
                "admin",
                "gate"
            ]
        )

        email = st.text_input(
            "Email"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

    if submitted:

        if role == "gate":

            st.session_state.logged_in = True

            st.session_state.user = {
                "name": "Gate Scanner",
                "email": "",
                "role": "gate",
                "id": None
            }

            st.session_state.page = "Scanner"

            st.rerun()

        user = get_user(
            email,
            password,
            role
        )

        if user:

            st.session_state.logged_in = True
            st.session_state.user = user

            if role == "student":
                st.session_state.page = "Dashboard"

            elif role == "parent":
                st.session_state.page = "Applications"

            elif role == "admin":
                st.session_state.page = "Dashboard"

            st.rerun()

        else:

            st.error(
                "Invalid email, password, or role."
            )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

def student_dashboard():

    user = st.session_state.user

    st.title(
        f"Welcome, {user['name']}"
    )

    applications = get_student_applications(
        user["id"]
    )

    permitted_dates = get_permitted_dates()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Applications",
            len(applications)
        )

    with col2:

        st.metric(
            "Approved",
            sum(
                application.status == "approved"
                for application in applications
            )
        )

    with col3:

        st.metric(
            "Pending",
            sum(
                application.status in [
                    "pending",
                    "otp_pending"
                ]
                for application in applications
            )
        )

    st.divider()

    st.subheader(
        "Permitted Outing Dates"
    )

    if permitted_dates:

        for permitted_date in permitted_dates:

            description = (
                permitted_date.description
                or "Campus permitted outing"
            )

            st.write(
                f"**{permitted_date.leave_date}** — "
                f"{description}"
            )

    else:

        st.info(
            "No permitted outing dates are currently available."
        )

    st.divider()

    st.subheader(
        "Your Leave Applications"
    )

    if not applications:

        st.info(
            "You have not submitted any leave applications."
        )

        return

    for application in applications:

        status_text = (
            application.status
            .replace("_", " ")
            .title()
        )

        with st.expander(
            f"{application.leave_date} — "
            f"{application.leave_type.title()} — "
            f"{status_text}"
        ):

            st.write(
                f"**Reason:** {application.reason}"
            )

            st.write(
                f"**Status:** {status_text}"
            )

            if application.parent_comment:

                st.write(
                    f"**Parent Comment:** "
                    f"{application.parent_comment}"
                )

            if application.status == "approved":

                show_qr(application)


# =========================================================
# STUDENT APPLY LEAVE
# =========================================================

def student_apply_leave():

    user = st.session_state.user

    st.title(
        "Apply for Leave"
    )

    permitted_dates = get_permitted_dates()

    permitted_date_values = [
        permitted_date.leave_date
        for permitted_date in permitted_dates
    ]

    leave_type = st.selectbox(
        "Leave Type",
        [
            "regular",
            "emergency"
        ],
        key="leave_type"
    )

    selected_date = st.date_input(
        "Leave Date",
        min_value=date.today(),
        key="leave_date_picker"
    )

    # Make absolutely sure the selected value is a
    # Python datetime.date object.
    if isinstance(selected_date, datetime):
        selected_date = selected_date.date()

    reason = st.text_area(
        "Reason",
        key="leave_reason"
    )

    if leave_type == "regular":

        st.info(
            "Regular leave is available only on "
            "administrator-permitted dates."
        )

        if permitted_date_values:

            st.write(
                "Available regular leave dates:"
            )

            st.write(
                ", ".join(
                    str(d)
                    for d in permitted_date_values
                )
            )

        else:

            st.warning(
                "There are currently no permitted dates "
                "for regular leave."
            )

    else:

        st.info(
            "Emergency leave does not require an "
            "administrator-permitted date."
        )

    if st.button(
        "Submit Leave Application",
        use_container_width=True
    ):

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not reason.strip():

            st.error(
                "Please enter a reason."
            )

            return

        if selected_date < date.today():

            st.error(
                "You cannot apply for a past date."
            )

            return

        # -------------------------------------------------
        # REGULAR LEAVE VALIDATION
        # -------------------------------------------------

        if (
            leave_type == "regular"
            and selected_date not in permitted_date_values
        ):

            st.error(
                "Regular leave is not permitted "
                "on this date."
            )

            return

        # -------------------------------------------------
        # DATABASE CHECK
        # -------------------------------------------------

        with flask_app.app_context():

            student_id = int(user["id"])

            # Explicit comparison instead of filter_by()
            # so the selected date and student are checked
            # independently and unambiguously.
            existing_application = (
                LeaveApplication.query
                .filter(
                    LeaveApplication.student_id == student_id,
                    LeaveApplication.leave_date == selected_date
                )
                .first()
            )

            if existing_application:

                existing_status = (
                    existing_application.status
                    .replace("_", " ")
                    .title()
                )

                st.error(
                    f"You already have a leave application "
                    f"for {selected_date}. "
                    f"Current status: {existing_status}."
                )

                return

            # -------------------------------------------------
            # CREATE NEW APPLICATION
            # -------------------------------------------------

            application = LeaveApplication(
                student_id=student_id,
                leave_date=selected_date,
                leave_type=leave_type,
                reason=reason.strip(),
                status="pending"
            )

            db.session.add(
                application
            )

            db.session.commit()

        st.success(
            f"Leave application for {selected_date} "
            "submitted successfully."
        )

        st.rerun()


# =========================================================
# QR DISPLAY
# =========================================================

def show_qr(application):

    qr_token = application.qr_token
    qr_used = application.qr_used
    leave_date = application.leave_date

    if not qr_token:

        with flask_app.app_context():

            current_application = LeaveApplication.query.get(
                application.id
            )

            if not current_application:
                st.error("Leave application could not be found.")
                return

            if not current_application.qr_token:
                current_application.qr_token = secrets.token_urlsafe(
                    32
                )
                current_application.qr_used = False
                db.session.commit()

            qr_token = current_application.qr_token
            qr_used = current_application.qr_used
            leave_date = current_application.leave_date

    qr_image = generate_qr_image(
        qr_token
    )

    image_stream = io.BytesIO()

    qr_image.save(
        image_stream,
        format="PNG"
    )

    image_stream.seek(0)

    st.image(
        image_stream,
        caption="Approved Outing QR Code",
        width=300
    )

    st.write(
        f"**Valid Date:** "
        f"{leave_date}"
    )

    if qr_used:

        st.error(
            "This QR code has already been used."
        )


# =========================================================
# PARENT DASHBOARD
# =========================================================

def parent_applications():

    user = st.session_state.user

    st.title(
        "Parent Dashboard"
    )

    with flask_app.app_context():

        applications = LeaveApplication.query.join(
            LeaveApplication.student
        ).filter(
            LeaveApplication.student.has(
                parent_id=user["id"]
            )
        ).order_by(
            LeaveApplication.leave_date.desc()
        ).all()

        if not applications:

            st.info(
                "There are no leave applications."
            )

            return

        for application in applications:

            student = application.student

            status_text = (
                application.status
                .replace("_", " ")
                .title()
            )

            with st.expander(
                f"{student.name} — "
                f"{application.leave_date} — "
                f"{status_text}"
            ):

                st.write(
                    f"**Leave Type:** "
                    f"{application.leave_type.title()}"
                )

                st.write(
                    f"**Reason:** "
                    f"{application.reason}"
                )

                if application.parent_comment:

                    st.write(
                        f"**Parent Comment:** "
                        f"{application.parent_comment}"
                    )

                if application.status in [
                    "pending",
                    "otp_pending"
                ]:

                    comment = st.text_area(
                        "Parent Comment",
                        key=f"comment_{application.id}"
                    )

                    if application.status == "pending":

                        col1, col2 = st.columns(2)

                        with col1:

                            if st.button(
                                "Approve",
                                key=f"approve_{application.id}",
                                use_container_width=True
                            ):

                                send_parent_otp(
                                    application.id,
                                    comment
                                )

                        with col2:

                            if st.button(
                                "Decline",
                                key=f"decline_{application.id}",
                                use_container_width=True
                            ):

                                application.status = "declined"

                                application.parent_comment = comment

                                application.otp_hash = None
                                application.otp_expires_at = None
                                application.otp_attempts = 0
                                application.qr_token = None
                                application.qr_used = False

                                db.session.commit()

                                st.success(
                                    "Leave application declined."
                                )

                                st.rerun()

                    elif application.status == "otp_pending":

                        verify_parent_otp(
                            application.id
                        )


# =========================================================
# SEND PARENT OTP
# =========================================================

def send_parent_otp(
    application_id,
    parent_comment
):

    user = st.session_state.user

    with flask_app.app_context():

        application = LeaveApplication.query.get_or_404(
            application_id
        )

        if application.student.parent_id != user["id"]:

            st.error(
                "Unauthorized."
            )

            return

        otp, otp_hash, expires_at = create_otp()

        application.status = "otp_pending"
        application.parent_comment = parent_comment
        application.otp_hash = otp_hash
        application.otp_expires_at = expires_at
        application.otp_attempts = 0
        application.qr_token = None
        application.qr_used = False

        db.session.commit()

        try:

            send_otp_email(
                recipient_email=user["email"],
                student_name=application.student.name,
                leave_date=application.leave_date,
                otp=otp
            )

            st.success(
                "OTP sent to your registered email address."
            )

        except Exception as error:

            application.status = "pending"
            application.otp_hash = None
            application.otp_expires_at = None
            application.otp_attempts = 0

            db.session.commit()

            st.error(
                f"Unable to send OTP: {error}"
            )


# =========================================================
# VERIFY PARENT OTP
# =========================================================

def verify_parent_otp(application_id):

    user = st.session_state.user

    st.markdown(
        "### OTP Verification"
    )

    otp = st.text_input(
        "Enter 6-digit OTP",
        max_chars=6,
        key=f"otp_{application_id}"
    )

    if st.button(
        "Verify OTP & Approve",
        key=f"verify_{application_id}",
        use_container_width=True
    ):

        with flask_app.app_context():

            application = LeaveApplication.query.get_or_404(
                application_id
            )

            if application.student.parent_id != user["id"]:

                st.error(
                    "Unauthorized."
                )

                return

            if application.status != "otp_pending":

                st.error(
                    "This application is not waiting "
                    "for OTP verification."
                )

                return

            if (
                not application.otp_expires_at
                or datetime.utcnow()
                > application.otp_expires_at
            ):

                application.status = "pending"
                application.otp_hash = None
                application.otp_expires_at = None
                application.otp_attempts = 0

                db.session.commit()

                st.error(
                    "OTP has expired. "
                    "Please start the approval process again."
                )

                return

            if application.otp_attempts >= 5:

                application.status = "pending"
                application.otp_hash = None
                application.otp_expires_at = None
                application.otp_attempts = 0

                db.session.commit()

                st.error(
                    "Too many incorrect OTP attempts."
                )

                return

            if (
                not otp.isdigit()
                or len(otp) != 6
                or not check_password_hash(
                    application.otp_hash,
                    otp
                )
            ):

                application.otp_attempts += 1

                db.session.commit()

                remaining = (
                    5 - application.otp_attempts
                )

                st.error(
                    f"Incorrect OTP. "
                    f"{remaining} attempt(s) remaining."
                )

                return

            application.status = "approved"
            application.otp_hash = None
            application.otp_expires_at = None
            application.otp_attempts = 0
            application.qr_token = secrets.token_urlsafe(32)
            application.qr_used = False

            db.session.commit()

            st.success(
                "OTP verified. "
                "Leave application approved successfully."
            )

            st.rerun()


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def admin_dashboard():

    st.title(
        "Admin Dashboard"
    )

    with flask_app.app_context():

        permitted_dates = PermittedDate.query.order_by(
            PermittedDate.leave_date.asc()
        ).all()

        # Convert permitted-date ORM objects to simple values before
        # the SQLAlchemy session closes. This prevents detached-object
        # problems during Streamlit's later rendering.
        permitted_date_rows = [
            {
                "id": item.id,
                "leave_date": item.leave_date,
                "description": item.description or ""
            }
            for item in permitted_dates
        ]

        applications = (
            LeaveApplication.query
            .options(joinedload(LeaveApplication.student))
            .order_by(
                LeaveApplication.leave_date.desc()
            )
            .all()
        )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Permitted Dates",
            len(permitted_dates)
        )

    with col2:

        st.metric(
            "Applications",
            len(applications)
        )

    st.divider()

    st.subheader(
        "Add Permitted Outing Date"
    )

    selected_date = st.date_input(
        "Date",
        min_value=date.today(),
        key="admin_date"
    )

    description = st.text_input(
        "Description",
        key="admin_description"
    )

    if st.button(
        "Add Date",
        use_container_width=True
    ):

        with flask_app.app_context():

            existing = PermittedDate.query.filter_by(
                leave_date=selected_date
            ).first()

            if existing:

                st.error(
                    "This date is already permitted."
                )

            else:

                permitted_date = PermittedDate(
                    leave_date=selected_date,
                    description=description.strip()
                )

                db.session.add(
                    permitted_date
                )

                db.session.commit()

                st.success(
                    "Permitted outing date added."
                )

                st.rerun()

    st.divider()

    st.subheader(
        "Permitted Dates"
    )

    for permitted_date in permitted_date_rows:

        col1, col2 = st.columns([4, 1])

        with col1:

            st.write(
                f"**{permitted_date['leave_date']}** — "
                f"{permitted_date['description']}"
            )

        with col2:

            if st.button(
                "Delete",
                key=f"delete_date_{permitted_date['id']}"
            ):

                with flask_app.app_context():

                    item = PermittedDate.query.get_or_404(
                        permitted_date["id"]
                    )

                    db.session.delete(
                        item
                    )

                    db.session.commit()

                st.rerun()

    st.divider()

    st.subheader(
        "Leave Applications"
    )

    if applications:

        for application in applications:

            status_text = (
                application.status
                .replace("_", " ")
                .title()
            )

            st.write(
                f"**{application.student.name}** | "
                f"{application.leave_date} | "
                f"{application.leave_type.title()} | "
                f"{status_text}"
            )

            st.caption(
                application.reason
            )

            st.divider()

    else:

        st.info(
            "No applications have been submitted."
        )


# =========================================================
# GATE SCANNER
# =========================================================

def gate_scanner():

    st.title(
        "Gate QR Scanner"
    )

    st.write(
        "Upload a QR code image to verify "
        "the student's outing approval."
    )

    uploaded_file = st.file_uploader(
        "Upload QR Code",
        type=[
            "png",
            "jpg",
            "jpeg"
        ]
    )

    if not uploaded_file:

        st.info(
            "Upload a QR image to begin verification."
        )

        return

    try:

        import cv2
        import numpy as np

        image_bytes = uploaded_file.read()

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        detector = cv2.QRCodeDetector()

        token, points, _ = detector.detectAndDecode(
            image
        )

        if not token:

            st.error(
                "Could not read a valid QR code."
            )

            return

        st.success(
            "QR code detected."
        )

        with flask_app.app_context():

            application = LeaveApplication.query.filter_by(
                qr_token=token
            ).first()

            if not application:

                st.error(
                    "Invalid QR code."
                )

                return

            if application.status != "approved":

                st.error(
                    "This leave application is not approved."
                )

                return

            if application.qr_used:

                st.error(
                    "This QR code has already been used."
                )

                return

            if application.leave_date != date.today():

                st.error(
                    f"This QR code is valid only on "
                    f"{application.leave_date}."
                )

                return

            application.qr_used = True

            db.session.commit()

            st.success(
                "QR code verified successfully."
            )

            st.write(
                f"**Student:** "
                f"{application.student.name}"
            )

            st.write(
                f"**Date:** "
                f"{application.leave_date}"
            )

            st.write(
                f"**Leave Type:** "
                f"{application.leave_type.title()}"
            )

    except Exception as error:

        st.error(
            f"QR verification error: {error}"
        )


# =========================================================
# MAIN APPLICATION
# =========================================================

if not st.session_state.logged_in:

    login_page()

else:

    user = st.session_state.user

    with st.sidebar:

        st.title(
            "Campus OMS"
        )

        st.write(
            f"**{user['name']}**"
        )

        st.write(
            user["role"].title()
        )

        st.divider()

        if user["role"] == "student":

            page = st.radio(
                "Menu",
                [
                    "Dashboard",
                    "Apply Leave"
                ]
            )

            st.session_state.page = page

        elif user["role"] == "parent":

            st.session_state.page = "Applications"

        elif user["role"] == "admin":

            st.session_state.page = "Dashboard"

        elif user["role"] == "gate":

            st.session_state.page = "Scanner"

        st.divider()

        if st.button(
            "Logout",
            use_container_width=True
        ):

            logout()

    if user["role"] == "student":

        if st.session_state.page == "Dashboard":

            student_dashboard()

        elif st.session_state.page == "Apply Leave":

            student_apply_leave()

    elif user["role"] == "parent":

        parent_applications()

    elif user["role"] == "admin":

        admin_dashboard()

    elif user["role"] == "gate":

        gate_scanner()