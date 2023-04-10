from flask import render_template, url_for, flash, redirect, request
from app import app, db, bcrypt
from app.forms import (
    SentryRegistrationForm,
    CardRegistrationForm,
    CircuitGenerationForm,
    LoginForm,
    CircuitSelectionForm,
    UpdateSentryForm,
    UpdateCardForm,
)
from .models import Sentry, Card, Shift, Supervisor
from datetime import datetime
import app.utils as utils
from flask_login import login_user, current_user, logout_user, login_required


SHIFT = False
CURRENT_CIRCUIT = None
SENTRY_CIRCUIT = None
CIRCUIT_COMPLETED = False
PATHS = None
START = 0
END = 0
ALARMS = None


@app.route("/", methods=["GET", "POST"])
@app.route("/home", methods=["GET", "POST"])
def home():
    form = LoginForm()

    if form.validate_on_submit():
        supervisor = Supervisor.query.filter_by(email=form.email.data).first()
        if supervisor and bcrypt.check_password_hash(
            supervisor.password, form.password.data
        ):
            login_user(supervisor, remember=form.remember.data)
            flash("Login successful.", "success")
            return (
                redirect(next_page)
                if (next_page := request.args.get("next"))
                else redirect(url_for("home"))
            )
        else:
            flash("Wrong credentials.", "danger")

    return render_template("home.html", title="Home", form=form)


@app.route("/circuit/create", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def create_route():
    form = CircuitGenerationForm()

    if form.validate_on_submit():
        sentries = form.shift_sentries.data
        cards = form.shift_cards.data
        if len(cards) != len(sentries):
            flash(
                "Number of selected sentries and cards must be equal.",
                "danger",
            )
        else:
            date = form.shift_date.data
            time = form.start.data
            assignments = [
                (sentries[x].full_name, cards[x].alias, cards[x].rfid_id)
                for x in range(len(cards))
            ]
            hours = int(form.shift_dur_hour.data)
            minutes = int(form.shift_dur_min.data)
            start, end, paths, circuit = utils.generate_route(
                sentries=assignments,
                start_date=date,
                start_time=time,
                shift_dur_hour=hours,
                shift_dur_min=minutes,
            )
            created_route = Shift(
                shift_start=start,
                shift_end=end,
                sentries=assignments,
                circuit=circuit,
                path_freqs=paths,
            )
            db.session.add(created_route)
            db.session.commit()
            flash("Circuit generated.", "success")
            return redirect(url_for("view_current_route"))

    return render_template(
        "generate-route.html", title="Generate Route", form=form
    )


@app.template_filter("readable")
def derive_date_time(epoch: int):
    return datetime.fromtimestamp(epoch).strftime("%d/%m/%Y, %H:%M:%S")


@app.template_filter("readable_day")
def derive_date(epoch: int):
    return datetime.fromtimestamp(epoch).strftime("%d/%m/%Y")


@app.template_filter("readable_time")
def derive_time(epoch: int):
    return datetime.fromtimestamp(epoch).strftime("%H:%M:%S")


@app.route("/circuit/view")
@login_required  # ensures that supervisor is logged in to access
def view_current_route():
    return render_template(
        "view-current-circuit.html",
        sentries=SENTRY_CIRCUIT,
        title="Current Route",
        index=0,
        paths=PATHS,
        start=START,
        end=END,
        completed=CIRCUIT_COMPLETED,
    )


@app.route("/circuit/logs")
@login_required  # ensures that supervisor is logged in to access
def view_all_circuits():
    shifts = Shift.query.all()
    return render_template("view-all-circuits.html", circuits=shifts)


@app.route("/circuit/logs/<int:shift_id>")
@login_required  # ensures that supervisor is logged in to access
def view_one_circuit(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    return render_template(
        "view-circuit.html",
        shift_id=shift.id,
        sentries=shift.circuit,
        title="Previous Route",
        index=0,
        paths=shift.path_freqs,
        start=shift.shift_start,
        end=shift.shift_end,
        completed=shift.completed,
    )


@app.route("/sentries/view")
@login_required  # ensures that supervisor is logged in to access
def view_all_sentries():
    sentries = Sentry.query.all()
    return render_template("view-all-sentries.html", sentries=sentries)


@app.route("/cards/view")
@login_required  # ensures that supervisor is logged in to access
def view_all_cards():
    cards = Card.query.all()
    return render_template("view-all-cards.html", cards=cards)


@app.route("/circuit/select", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def select_circuit():
    form = CircuitSelectionForm()

    if form.validate_on_submit():
        circuit = form.circuit.data

        global SHIFT
        SHIFT = True
        global CURRENT_CIRCUIT
        CURRENT_CIRCUIT = circuit.id
        global SENTRY_CIRCUIT
        SENTRY_CIRCUIT = circuit.circuit
        global PATHS
        PATHS = circuit.path_freqs
        global START
        START = circuit.shift_start
        global END
        END = circuit.shift_end
        flash("Shift set!", "success")
        return redirect(url_for("view_current_route"))

    return render_template(
        "select-circuit.html",
        title="Select Circuit",
        form=form,
    )


@app.route("/circuit/save", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def save_current_circuit():
    circuit = Shift.query.get_or_404(CURRENT_CIRCUIT)
    circuit.circuit = SENTRY_CIRCUIT
    db.session.commit()
    flash("Current circuit saved.", "success")
    return redirect(url_for("view_current_route"))


@app.route("/circuit/deselect")
@login_required  # ensures that supervisor is logged in to access
def deselect_circuit():
    global SHIFT
    SHIFT = False
    global CURRENT_CIRCUIT
    CURRENT_CIRCUIT = None
    global SENTRY_CIRCUIT
    SENTRY_CIRCUIT = None
    global START
    START = 0
    global END
    END = 0
    flash("Shift Deselected.", "info")
    return redirect(url_for("select_circuit"))


@app.route("/circuit/logs/<int:shift_id>/delete", methods=["POST"])
@login_required  # ensures that supervisor is logged in to access
def delete_circuit(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    db.session.delete(shift)
    db.session.commit()
    flash("Shift Deleted.", "danger")
    return redirect(url_for("view_all_circuits"))


@app.route("/sentries/register", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def register_sentry():
    form = SentryRegistrationForm()

    if form.validate_on_submit():
        sentry = Sentry(
            national_id=form.national_id.data,
            full_name=form.full_name.data,
            phone_no=form.phone_no.data,
        )
        db.session.add(sentry)
        db.session.commit()
        flash("Sentry registered successfully.", "success")
        return redirect(url_for("home"))

    return render_template(
        "register-sentry.html",
        title="Register Sentry",
        form=form,
        legend="Register Sentry",
    )


@app.route("/sentries/view/<int:sentry_id>/update", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def update_sentry(sentry_id):
    sentry = Sentry.query.get_or_404(sentry_id)

    form = UpdateSentryForm(obj=sentry)

    if form.validate_on_submit():
        form.populate_obj(sentry)
        db.session.commit()
        flash("Sentry information updated.", "success")
        return redirect(url_for("home"))

    return render_template(
        "register-sentry.html",
        title="Update Sentry",
        form=form,
        legend="Update Sentry",
    )


@app.route("/cards/register", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def register_card():
    form = CardRegistrationForm()

    if form.validate_on_submit():
        card = Card(rfid_id=form.card_id.data, alias=form.alias.data)
        db.session.add(card)
        db.session.commit()
        flash("Card registered successfully.", "success")
        return redirect(url_for("home"))

    return render_template(
        "register-card.html",
        title="Register Card",
        form=form,
        legend="Registed RFID Card",
    )


@app.route("/cards/view/<int:card_id>/update", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def update_card(card_id):
    card = Card.query.get_or_404(card_id)

    form = UpdateCardForm(obj=card)

    if form.validate_on_submit():
        form.populate_obj(card)
        db.session.commit()
        flash("Card information updated.", "success")
        return redirect(url_for("home"))

    return render_template(
        "register-card.html",
        title="Update Card",
        form=form,
        legend="Update Card",
    )


@app.route("/logout")
@login_required  # ensures that supervisor is logged in to access
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


@app.route("/sentries/view/<int:sentry_id>/delete", methods=["POST"])
@login_required  # ensures that supervisor is logged in to access
def delete_sentry(sentry_id):
    sentry = Sentry.query.get_or_404(sentry_id)
    db.session.delete(sentry)
    db.session.commit()
    flash("Sentry Deleted.", "danger")
    return redirect(url_for("view_all_sentries"))


@app.route("/cards/view/<int:card_id>/delete", methods=["POST"])
@login_required  # ensures that supervisor is logged in to access
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Card Deleted.", "danger")
    return redirect(url_for("view_all_cards"))


password = "$2b$12$PqffSm1f9TGFmU0MwYTCXOz70YS3XjeW0B6iYybiv6IBlZpqjV59O"
