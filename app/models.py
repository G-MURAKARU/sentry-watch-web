from ast import literal_eval
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, Column, Integer, String, Text

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
        return f"{self.rfid_id}"


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
    ___tablename__ = "supervisors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(50), unique=True, nullable=False)
    password = Column(String(20), nullable=False)
