from app import create_app
from app.extensions import db
from app.models import User


app = create_app()


with app.app_context():

    # -----------------------------------------------------
    # WARNING
    # -----------------------------------------------------
    # This script is intended for initializing a fresh
    # development/production database.
    #
    # It deletes existing users.
    # -----------------------------------------------------

    User.query.delete()

    db.session.commit()

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    admin = User(
        name="System Administrator",
        email="admin@outing.com",
        role="admin"
    )

    admin.set_password(
        "Admin@123"
    )

    # -----------------------------------------------------
    # PARENT
    # -----------------------------------------------------

    parent = User(
        name="Parent User",
        email="parent@outing.com",
        role="parent"
    )

    parent.set_password(
        "Parent@123"
    )

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    student = User(
        name="Student User",
        email="student@outing.com",
        role="student",
        parent=parent
    )

    student.set_password(
        "Student@123"
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    db.session.add(admin)
    db.session.add(parent)
    db.session.add(student)

    db.session.commit()

    print()
    print("================================")
    print("Database seeded successfully!")
    print("================================")
    print()

    print("ADMIN")
    print("Email: admin@outing.com")
    print("Password: Admin@123")
    print()

    print("PARENT")
    print("Email: parent@outing.com")
    print("Password: Parent@123")
    print()

    print("STUDENT")
    print("Email: student@outing.com")
    print("Password: Student@123")
    print()