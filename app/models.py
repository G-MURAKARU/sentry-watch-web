from ast import literal_eval
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app import db, login_manager


# to manage supervisor's login session
@login_manager.user_loader
def load_supervisor(supervisor_id):
    return Supervisor.query.get(int(supervisor_id))


class Sentry(db.Model):
    __tablename__ = "sentries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    national_id = Column(String(8), unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_no = Column(String(13), nullable=False)

    def __repr__(self) -> str:
        return f"Sentry(ID: '{self.national_id}', Name: '{self.full_name}', Tel: '{self.phone_no}')"


class Card(db.Model):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfid_id = Column(String(11), unique=True, nullable=False)
    alias = Column(String(20), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"Card(ID: '{self.rfid_id}', Alias: '{self.alias}')"


class Shift(db.Model):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shift_start = Column(Integer, nullable=False, unique=True)
    shift_end = Column(Integer, nullable=False)
    _sentries_on_duty = Column(Text, nullable=False)
    _circuit = Column(Text, nullable=False)
    _path_freqs = Column(Text, nullable=False)
    _alarms = Column(Text, nullable=False, default="[]")
    completed = Column(Boolean, nullable=False, default=False)

    # since one cannot store data structures (dicts, lists) in the database,
    # they are first 'stringified' -> converted to strings
    # hence the setters -> @column.setter

    # but when they are 'queried' they are first re-converted to the original
    # data structure using literal_eval()
    # hence the getters -> @property

    # originally a list of tuples
    @property
    def sentries(self):
        return literal_eval(self._sentries_on_duty)

    @sentries.setter
    def sentries(self, on_duty):
        self._sentries_on_duty = str(on_duty)

    # originally a list of dicts
    @property
    def circuit(self):
        return literal_eval(self._circuit)

    @circuit.setter
    def circuit(self, route):
        self._circuit = str(route)

    # originally a list of tuples
    @property
    def path_freqs(self):
        return literal_eval(self._path_freqs)

    @path_freqs.setter
    def path_freqs(self, path):
        self._path_freqs = str(path)

    # originally a list of ints
    @property
    def alarms(self):
        return literal_eval(self._alarms)

    @alarms.setter
    def alarms(self, alarm):
        self._alarms = str(alarm)

    # this will be used to format the appearance of the shift in the form for selecting a circuit
    def __str__(self) -> str:
        day_time = datetime.fromtimestamp(self.shift_start)
        day = day_time.strftime("%d/%m/%Y")
        time = day_time.strftime("%H:%M:%S")
        return f"{day}, {time}"


class Supervisor(db.Model, UserMixin):
    __tablename__ = "supervisors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(50), unique=True, nullable=False)
    password = Column(String(20), nullable=False)


class Checkpoint(db.Model):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    patrol_paths_in = relationship(
        "PatrolPath",
        foreign_keys="PatrolPath.chkpt_src",
        # primaryjoin="PatrolPath.chkpt_src == id",
        backref="src_checkpoint",
        cascade="all, delete",
    )

    patrol_paths_out = relationship(
        "PatrolPath",
        foreign_keys="PatrolPath.chkpt_dest",
        # primaryjoin="PatrolPath.chkpt_dest == id",
        backref="dest_checkpoint",
        cascade="all, delete",
    )

    @property
    def paths_out(self):
        return [
            (patrol_path.dest_checkpoint.name, patrol_path.duration)
            for patrol_path in self.patrol_paths_in
        ]

    def append_path_out(self, path: tuple[str, int]):
        dest_checkpoint = Checkpoint.query.filter_by(name=path[0]).first()
        patrol_path = PatrolPath(chkpt_src=self.id, chkpt_dest=dest_checkpoint.id, duration=path[1])
        db.session.add(patrol_path)


class PatrolPath(db.Model):
    __tablename__ = "ptrl_paths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chkpt_src = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)
    chkpt_dest = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)
    duration = Column(Integer, nullable=False)

    # src_checkpoint = relationship(
    #     "Checkpoint",
    #     foreign_keys=chkpt_src,
    #     back_populates="patrol_paths_in"
    # )
    # dest_checkpoint = relationship(
    #     "Checkpoint",
    #     foreign_keys=chkpt_dest,
    #     back_populates="patrol_paths_out"
    # )

    __table_args__ = (UniqueConstraint("chkpt_src", "chkpt_dest", name="_ptrl_path_uc"),)

    def __str__(self):
        """
        set how a path will appear when queried and displayed on the frontend
        """

        return f"from: {self.src_checkpoint.name} ; to: {self.dest_checkpoint.name} ; dur: {self.duration / 60}min"
