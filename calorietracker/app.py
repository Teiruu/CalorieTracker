from collections.abc import async_generator

from flask import Flask, render_template, redirect, request, url_for, session
from flask_session import Session
from model.base import db, Base
from model.models import Register, User, CalorieLog, CalorieLogForm, LoginForm

# create the app
app = Flask(__name__)

app.config.from_pyfile('instance/config.py')  # Load additional config

# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

# initialize the app with the extension
db.init_app(app)

#Login session config/initialize
app.config["SESSION_PERMANENT"] = False     # Sessions expire when the browser is closed
app.config["SESSION_TYPE"] = "filesystem"     # Store session data in files

# Initialize Flask-Session
Session(app)

# Ensure database tables are created on startup
with app.app_context():
    db.create_all()
    db.session.commit()
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if not session.get("username"):
        return redirect("/")
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get("username"):
        return redirect("/dashboard")
    form = LoginForm()
    if form.validate_on_submit():
        session["username"] = request.form.get("username")
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
        #Adds user to the DB
        db.session.add(user)
        db.session.commit()
        session["username"] = request.form.get("username")
        return redirect(url_for('dashboard'))
    return render_template('register.html', form=form)

@app.route("/logout", methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app()