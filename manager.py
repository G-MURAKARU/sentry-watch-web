#!/usr/bin/python3
from sys import argv
from app import app, db
from app.models import Supervisor, Checkpoint
from flask_bcrypt import bcrypt


class Manager():
    def create_supervisor():
        with app.app_context():
            # To create supervisor login if none exist
            if Supervisor.query.count() == 0:
                print ("Adding supervisor")
                new_supervisor = Supervisor(
                    email="supervisor@company.com",
                    password=bcrypt.generate_password_hash("Master0Pass").decode("utf-8"),
                )
                db.session.add(new_supervisor)
                db.session.commit()

    def add_checkpoint():
        with app.app_context():
            # To create Checkpoints if none exist
            if Checkpoint.query.count() == 0:
                print ("Adding checkpoints")
                checks = [
                    Checkpoint(id=0, name="Checkpoint A"),  # 0
                    Checkpoint(id=1, name="Checkpoint B"),  # 1
                    Checkpoint(id=2, name="Checkpoint C"),  # 2
                    Checkpoint(id=3, name="Checkpoint D"),  # 3
                    Checkpoint(id=4, name="Checkpoint E"),  # 4
                    Checkpoint(id=5, name="Checkpoint F"),  # 5
                    Checkpoint(id=6, name="Checkpoint G"),  # 6
                    Checkpoint(id=7, name="Checkpoint H"),  # 7
                    Checkpoint(id=8, name="Checkpoint I"),  # 8
                ]
                db.session.add_all(checks)
                db.session.commit()

                print ("Adding patrol paths")
                # Setting a rectangular grid with naming going left-to-right then top-to-bottom
                GRID_WIDTH = 3
                for i in range(len(checks)):
                    # Checkpoint leftwards
                    if (i % GRID_WIDTH) > 0:
                        checks[i].append_path_out((checks[i - 1].name, 90))
                    # Checkpoint upwards
                    if i >= GRID_WIDTH:
                        if i < (2 * GRID_WIDTH):  # First vertical is 60 duration
                            checks[i].append_path_out((checks[i - GRID_WIDTH].name, 60))
                        else:
                            checks[i].append_path_out((checks[i - GRID_WIDTH].name, 70))
                    # Checkpoint rightwards
                    if (i + 1) < len(checks) and ((i + 1) % GRID_WIDTH) > 0:
                        checks[i].append_path_out((checks[i + 1].name, 90))
                    # Checkpoint downwards
                    if (i + GRID_WIDTH) < len(checks):
                        if i < GRID_WIDTH:  # First vertical is 60 duration
                            checks[i].append_path_out((checks[i + GRID_WIDTH].name, 60))
                        else:
                            checks[i].append_path_out((checks[i + GRID_WIDTH].name, 70))
                db.session.commit()

    def recreate_db():
        """
        Recreates a local database. You probably should not use this on
        production.
        """
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.commit()


def manager():
    """My main function
    """
    argc = len(argv)
    if argc <= 1:
        print("Select the command to execute:")
        print(*["\t{}".format(k) for k,v in  Manager.__dict__.items() if hasattr(v, "__call__")], sep = "\n")
    else:
        if argc > 2:
            print("Only one command at a time (Running the first)")
        eval("Manager.{}()".format(argv[1]))


if __name__ == "__main__":
    manager()
