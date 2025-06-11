from collections.abc import async_generator

from flask import Flask, render_template, redirect, request, url_for, session, flash, jsonify, abort
from flask_session import Session
from model.base import db, Base
from model.models import Register, User, CalorieLog, CalorieLogForm, LoginForm, ExerciseLog, ExerciseLogForm, AddFoodForm, FindFoodForm, TimeOfDay, ProductList
from datetime import datetime, date
from sqlalchemy import func
import pytz

# create the app
app = Flask(__name__)

app.config.from_pyfile('instance/config.py')  # Load additional config

# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

# initialize the app with the extension
db.init_app(app)

# Login session config/initialize
app.config["SESSION_PERMANENT"] = False  # Sessions expire when the browser is closed
app.config["SESSION_TYPE"] = "filesystem"  # Store session data in files

# Initialize Flask-Session
Session(app)

# Ensure database tables are created on startup
with app.app_context():
    db.create_all()
    db.session.commit()


def calculate_daily_calorie_goal(user):
    # 1) BMR
    if user.gender == 'male':
        bmr = 10 * float(user.weight) + 6.25 * user.height - 5 * user.age + 5
    else:
        bmr = 10 * float(user.weight) + 6.25 * user.height - 5 * user.age - 161

    # 2) activity multiplier
    mult = {'none': 1.2, 'some': 1.375, 'alot': 1.55}[user.activity_level]
    tdee = bmr * mult

    # 3) adjust for goal
    if user.goal == 'lose':
        return int(tdee - 500)
    elif user.goal == 'gain':
        return int(tdee + 500)
    else:
        return int(tdee)


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))

    today = date.today()

    # total food calories today
    consumed = (
        db.session.query(func.coalesce(func.sum(CalorieLog.calories), 0))
          .filter(
            CalorieLog.user_id == user_id,
            func.date(CalorieLog.created_at) == today
          )
          .scalar()
    )

    # total exercise calories today
    exercise = (
        db.session.query(func.coalesce(func.sum(ExerciseLog.calories), 0))
          .filter(
            ExerciseLog.user_id == user_id,
            func.date(ExerciseLog.created_at) == today
          )
          .scalar()
    )

    remaining = user.calorie_goal - consumed + exercise

    # **ALL** today's food entries
    calorie_logs = (
        db.session.query(CalorieLog)
          .filter(
            CalorieLog.user_id == user_id,
            func.date(CalorieLog.created_at) == today
          )
          .order_by(CalorieLog.created_at.desc())
          .all()
    )

    # **ALL** today's exercise entries
    exercise_logs = (
        db.session.query(ExerciseLog)
          .filter(
            ExerciseLog.user_id == user_id,
            func.date(ExerciseLog.created_at) == today
          )
          .order_by(ExerciseLog.created_at.desc())
          .all()
    )

    return render_template(
        'dashboard.html',
        calorie_goal=user.calorie_goal,
        consumed=consumed,
        exercise=exercise,
        remaining=remaining,
        calorie_logs=calorie_logs,
        exercise_logs=exercise_logs
    )
@app.route('/exercise', methods=['GET', 'POST'])
def add_exercise():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    form = ExerciseLogForm()
    if form.validate_on_submit():
        log = ExerciseLog(
            user_id=session['user_id'],
            calories=form.calories.data,
            notes=form.notes.data
        )
        db.session.add(log)
        db.session.commit()
        flash('Exercise entry added!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_exercise.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get("user_id"):
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        # find the user
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data)
        ).scalar_one()

        # store *both* id and username
        session["user_id"] = user.id
        session["username"] = user.username

        return redirect(url_for('dashboard'))

    return render_template('login.html', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if session.get("username"):
        return redirect("/dashboard")
    form = Register()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            firstname=form.firstname.data,
            lastname=form.lastname.data,
            age=form.age.data,
            gender=form.gender.data,
            height=form.height.data,
            weight=form.weight.data,
            activity_level=form.activity_level.data,
            goal=form.goal.data
        )
        user.set_password(form.password.data)
        user.calorie_goal = calculate_daily_calorie_goal(user)
        # Adds user to the DB
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect(url_for('dashboard'))

    return render_template('register.html', form=form)


@app.route("/logout", methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/add_food_basic', methods=['GET','POST'])
def add_food_basic():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    form = AddFoodForm()

    # ——— PREFILL if coming from /find_food?prefill=<id> ———
    pid = request.args.get('prefill', type=int)
    if pid and request.method == 'GET':
        p = ProductList.query.get(pid)
        if p:
            form.product.data   = p.product_name or ''
            form.size.data      = p.product_size   or ''
            form.quantity.data  = 1
            form.calories.data  = int(p.calories_kcal   or 0)
            form.fat.data       = float(p.fat_g          or 0)
            form.saturated.data = float(p.saturated_fat_g or 0)
            form.carbs.data     = float(p.carbohydrates_g or 0)
            form.sugars.data    = float(p.sugars_g       or 0)
            form.protein.data   = float(p.protein_g      or 0)
            form.salt.data      = float(p.salt_g         or 0)
            form.fiber.data     = float(p.fiber_g        or 0)
    # ————————————————————————————————————————————

    if form.validate_on_submit():
        q = form.quantity.data
        log = CalorieLog(
            user_id     = session['user_id'],
            product     = form.product.data,
            time_of_day = TimeOfDay[form.time_of_day.data],
            quantity    = q,
            calories    = form.calories.data * q,
            fat         = form.fat.data * q         if form.fat.data else None,
            saturated   = form.saturated.data * q   if form.saturated.data else None,
            carbs       = form.carbs.data * q       if form.carbs.data else None,
            sugars      = form.sugars.data * q      if form.sugars.data else None,
            protein     = form.protein.data * q     if form.protein.data else None,
            salt        = form.salt.data * q        if form.salt.data else None,
            fiber       = form.fiber.data * q       if form.fiber.data else None,
            notes       = form.notes.data
        )
        db.session.add(log)
        db.session.commit()
        flash(f"Added {q}× {log.product}", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_food_basic.html', form=form)

@app.route('/find_food', methods=['GET','POST'])
def find_food():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    form    = FindFoodForm()
    results = None

    if form.validate_on_submit():
        code = form.code_lookup.data
        name = request.form.get('name_lookup','').strip()

        if code:
            results = ProductList.query.filter_by(
                product_code=int(code)
            ).all()
        elif name:
            results = (ProductList.query
                       .filter(ProductList.product_name.ilike(f'%{name}%'))
                       .all())
        else:
            flash('Please enter a barcode or start typing a name.', 'warning')

    return render_template('find_food.html',
                           form=form,
                           results=results)

@app.route('/api/products')
def product_autocomplete():
    q = request.args.get('q','').strip()
    if not q:
        return jsonify([])
    # grab up to 10 matching names
    names = (db.session.query(ProductList.product_name)
             .filter(ProductList.product_name.ilike(f'%{q}%'))
             .distinct()
             .limit(10)
             .all())
    return jsonify([n.product_name for n in names])

@app.route('/choose_food')
def choose_food():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('choose_food.html')

@app.route('/delete_food/<int:log_id>', methods=['POST'])
def delete_food(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    log = db.session.get(CalorieLog, log_id)
    # not found or not theirs → 404
    if log is None or log.user_id != session['user_id']:
        abort(404)

    db.session.delete(log)
    db.session.commit()
    flash('Food entry deleted', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/delete_exercise/<int:log_id>', methods=['POST'])
def delete_exercise(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    log = db.session.get(ExerciseLog, log_id)
    if log is None or log.user_id != session['user_id']:
        abort(404)

    db.session.delete(log)
    db.session.commit()
    flash('Exercise entry deleted', 'warning')
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app()

