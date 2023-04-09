from flask import render_template, url_for, flash, redirect, request
from app import app, db, bcrypt
from app.forms import (
    SentryRegistrationForm,
    CardRegistrationForm,
    CircuitGenerationForm,
    LoginForm,
    CircuitSelectionForm,
)
from .models import Sentry, Card, Shift, Supervisor
from datetime import datetime
import app.utils as utils
from flask_login import login_user, current_user, logout_user, login_required


SHIFT = False
CURRENT_CIRCUIT = None
SENTRY_ROUTE = None
PATHS = None
START = 0
END = 0
ALARMS = None


@app.route("/")
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

    return render_template("home.html", title="Home", form=form, shift=SHIFT)


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
                (sentries[x].full_name, cards[x].rfid_id)
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
        "generate-route.html", title="Generate Route", form=form, shift=SHIFT
    )


@app.template_filter("readable")
def derive_date_time(epoch: int):
    return datetime.fromtimestamp(epoch).strftime("%d/%m/%Y, %H:%M:%S")


@app.route("/circuit/view")
@login_required  # ensures that supervisor is logged in to access
def view_current_route():
    return render_template(
        "view-current-route.html",
        sentries=SENTRY_ROUTE,
        title="Current Route",
        index=0,
        paths=PATHS,
        shift=SHIFT,
        start=START,
        end=END,
    )


@app.route("/circuit/logs")
@login_required  # ensures that supervisor is logged in to access
def view_all_circuits():
    shifts = Shift.query.all()


@app.route("/circuit/logs/<int:shift_id>")
@login_required  # ensures that supervisor is logged in to access
def view_one_circuit(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    return render_template(
        "view-route.html",
        sentries=shift.circuit,
        title="Previous Route",
        index=0,
        paths=shift.path_freqs,
        start=shift.shift_start,
        end=shift.shift_end,
    )


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
        shift=SHIFT,
    )


@app.route("/cards/register", methods=["GET", "POST"])
@login_required  # ensures that supervisor is logged in to access
def register_card():
    form = CardRegistrationForm()

    if form.validate_on_submit():
        card = Card(rfid_id=form.card_id.data)
        db.session.add(card)
        db.session.commit()
        flash("Card registered successfully.", "success")
        return redirect(url_for("home"))

    return render_template(
        "register-card.html", title="Register Sentry", form=form, shift=SHIFT
    )


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
        global SENTRY_ROUTE
        SENTRY_ROUTE = circuit.circuit
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
        shift=SHIFT,
    )


@app.route("/circuit/save")
@login_required  # ensures that supervisor is logged in to access
def save_circuit():
    pass


@app.route("/circuit/deselect")
@login_required  # ensures that supervisor is logged in to access
def deselect_circuit():
    global SHIFT
    SHIFT = False
    global CURRENT_CIRCUIT
    CURRENT_CIRCUIT = None
    global SENTRY_ROUTE
    SENTRY_ROUTE = None
    global START
    START = 0
    global END
    END = 0
    flash("Shift Deselected.", "info")
    return redirect(url_for("select_circuit"))


@app.route("/circuit/delete")
@login_required  # ensures that supervisor is logged in to access
def delete_circuit():
    global SHIFT
    SHIFT = False
    global SENTRY_ROUTE
    SENTRY_ROUTE = None
    global START
    START = 0
    global END
    END = 0
    flash("Shift Deleted.", "danger")
    return redirect(url_for("home"))


@app.route("/logout")
@login_required  # ensures that supervisor is logged in to access
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("home"))


password = "$2b$12$PqffSm1f9TGFmU0MwYTCXOz70YS3XjeW0B6iYybiv6IBlZpqjV59O"
