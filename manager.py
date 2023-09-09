from app import app, db
from app.models import Supervisor
from flask_script import Manager
from flask_bcrypt import bcrypt

manager = Manager(app=app)


@manager.command
def seed():
    if Supervisor.query.count() == 0:
        new_supervisor = Supervisor(
            email="supervisor@sentrywatch.com",
            password=bcrypt.generate_password_hash("Master0Pass").decode("utf-8"),
        )
        db.session.add(new_supervisor)
        db.session.commit()


if __name__ == "__main__":
    manager.run()
