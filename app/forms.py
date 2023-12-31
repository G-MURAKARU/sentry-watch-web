from datetime import datetime
import phonenumbers

from flask import request
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TimeField,
    IntegerField,
)
from wtforms.validators import Email, InputRequired, Length, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from app.models import Card, Sentry, Shift, PatrolPath, Checkpoint


def validate_phone_number(form, phone_no: str) -> None:
    """
    validates an input phone number using the phonenumbers python library
    """

    try:
        input_number = phonenumbers.parse(phone_no.data)
    except phonenumbers.NumberParseException as error:
        raise ValidationError("Input valid phone number.") from error
    else:
        if not phonenumbers.is_valid_number(input_number):
            raise ValidationError("Input valid phone number.")


class SentryRegistrationForm(FlaskForm):
    """
    Registration form for sentries
    """

    national_id = StringField(
        "National ID",
        validators=[
            InputRequired(),
            Length(min=7, max=8, message="Input valid National ID"),
        ],
    )
    full_name = StringField("Full Name", validators=[InputRequired()])
    phone_no = StringField(
        "Phone Number",
        validators=[
            InputRequired(),
            validate_phone_number,
        ],
        description="format: e.g. +254...",
    )
    submit = SubmitField("Register")

    def validate_national_id(self, national_id):
        if Sentry.query.filter_by(national_id=national_id.data).first():
            raise ValidationError(f"Sentry with ID: {national_id.data} already registered.")


class UpdateSentryForm(FlaskForm):
    """
    Update form for sentries
    """

    national_id = StringField(
        "National ID",
        validators=[
            InputRequired(),
            Length(min=7, max=8, message="Input valid National ID"),
        ],
    )
    full_name = StringField("Full Name", validators=[InputRequired()])
    phone_no = StringField(
        "Phone Number",
        validators=[
            InputRequired(),
            Length(min=13, max=13, message="Input valid phone number"),
        ],
        description="format: e.g. +254...",
    )
    submit = SubmitField("Update")

    def validate_national_id(self, national_id):
        sentry = Sentry.query.filter_by(national_id=national_id.data).first()
        query_id = int(request.url.split("/")[5])
        if sentry and sentry.id != query_id:
            raise ValidationError(f"Sentry with ID: {national_id.data} already registered.")


class CardRegistrationForm(FlaskForm):
    """
    Registration form for (RFID) ID cards
    """

    rfid_id = StringField(
        "Card ID",
        validators=[
            InputRequired(),
            Length(min=11, max=11, message="Input valid card ID"),
        ],
    )
    alias = StringField("Card Alias/Name", validators=[InputRequired()])
    submit = SubmitField("Register")

    def validate_rfid_id(self, rfid_id):
        if Card.query.filter_by(rfid_id=rfid_id.data).first():
            raise ValidationError(f"Card with ID: {rfid_id.data} already registered.")

    def validate_alias(self, alias):
        if Card.query.filter_by(alias=alias.data).first():
            raise ValidationError(f"Card with alias: {alias.data} already registered.")


class UpdateCardForm(FlaskForm):
    """
    Registration form for (RFID) ID cards
    """

    rfid_id = StringField(
        "Card ID",
        validators=[
            InputRequired(),
            Length(min=11, max=11, message="Input valid card ID"),
        ],
    )
    alias = StringField("Card Alias/Name", validators=[InputRequired()])
    submit = SubmitField("Update")

    def validate_card_id(self, rfid_id):
        card = Card.query.filter_by(rfid_id=rfid_id.data).first()
        query_id = int(request.url.split("/")[5])
        if card and card.id != query_id:
            raise ValidationError(f"Card with ID: {rfid_id.data} already registered.")

    def validate_alias(self, alias):
        card = Card.query.filter_by(alias=alias.data).first()
        query_id = int(request.url.split("/")[5])
        if card and card.id != query_id:
            raise ValidationError(f"Card with alias: {alias.data} already registered.")


class LoginForm(FlaskForm):
    """
    Login form for the monitoring platform
    """

    email = StringField(
        "Email",
        validators=[
            InputRequired(),
            Email(message="Input valid email address"),
        ],
    )
    password = PasswordField("Password", validators=[InputRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


def validate_date(form, date):
    if date.data < datetime.date(datetime.now()):
        raise ValidationError("Invalid date.")


class CircuitGenerationForm(FlaskForm):
    """
    Circuit information collection form to generate sentry circuit
    """

    shift_date = DateField(
        "Shift Date",
        default=datetime.date(datetime.now()),
        validators=[InputRequired(), validate_date],
    )

    start = TimeField(
        "Shift Start",
        default=datetime.time(datetime.now()),
        validators=[InputRequired()],
    )
    shift_dur_hour = SelectField(
        "Shift Duration (Hours)",
        validators=[InputRequired()],
        choices=range(1, 24),
        validate_choice=True,
    )
    shift_dur_min = SelectField(
        "Shift Duration (Minutes)",
        validators=[InputRequired()],
        choices=range(60),
        validate_choice=True,
    )
    shift_sentries = QuerySelectMultipleField(
        "Sentries",
        query_factory=lambda: Sentry.query.all(),
        allow_blank=False,
        get_label="full_name",
        validators=[InputRequired()],
    )
    shift_cards = QuerySelectMultipleField(
        "Cards",
        query_factory=lambda: Card.query.all(),
        allow_blank=False,
        get_label="alias",
        validators=[InputRequired()],
    )
    shift_paths = QuerySelectMultipleField(
        "Patrol Paths",
        query_factory=lambda: PatrolPath.query.all(),
        allow_blank=False,
        validators=[InputRequired()],
    )
    submit = SubmitField("Generate Circuit")

    def validate(self, extra_validators=None):
        valid = FlaskForm.validate(self)
        if not valid:
            return False

        if datetime.combine(self.shift_date.data, self.start.data) < datetime.now():
            self.start.errors.append("Invalid time.")
            return False

        return True


class CircuitSelectionForm(FlaskForm):
    """
    Circuit selection from pre-defined circuits
    """

    circuit = QuerySelectField(
        "Circuit",
        query_factory=lambda: Shift.query.filter(Shift.completed == False)
        .filter(Shift.shift_end > datetime.timestamp(datetime.now()))
        .order_by(Shift.shift_start)
        .all(),
        allow_blank=False,
        validators=[InputRequired()],
    )
    submit = SubmitField("Select Circuit")


class CheckpointRegistrationForm(FlaskForm):
    """
    Registration form for Premises' Checkpoints
    """

    chk_id = IntegerField("Checkpoint ID", validators=[InputRequired()])
    chk_name = StringField("Checkpoint Name", validators=[InputRequired()])
    submit = SubmitField("Register")

    def validate_chk_id(self, chk_id):
        if Checkpoint.query.filter_by(id=chk_id.data).first():
            raise ValidationError(f"Checkpoint with ID: {chk_id.data} already registered.")

    def validate_chk_name(self, chk_name):
        if Checkpoint.query.filter_by(name=chk_name.data).first():
            raise ValidationError(f"Checkpoint with name: {chk_name.data} already registered.")


class PathCreationForm(FlaskForm):
    """
    Creation form for a sentry path: start checkpoint, end checkpoint, duration
    """

    start = QuerySelectField(
        "Start Checkpiont",
        query_factory=lambda: Checkpoint.query.all(),
        allow_blank=False,
        get_label="name",
        validators=[InputRequired()],
    )
    end = QuerySelectField(
        "Destination Checkpoint",
        query_factory=lambda: Checkpoint.query.all(),
        allow_blank=False,
        get_label="name",
        validators=[InputRequired()],
    )
    duration = IntegerField("Patrol Duration", validators=[InputRequired()])
    submit = SubmitField("Add Path")

    def validate(self, extra_validators=None):
        valid = FlaskForm.validate(self)
        if not valid:
            return False

        if self.start.data == self.end.data:
            self.end.errors.append("Start and destination checkpoints should differ.")
            return False

        if self.duration.data < 1:
            self.duration.errors.append("Duration must be a minute at least.")
            return False

        return True
