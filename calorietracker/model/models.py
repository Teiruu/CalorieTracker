from flask_wtf import FlaskForm
from sqlalchemy import Integer, String, ForeignKey, Numeric, Enum
from sqlalchemy.orm import mapped_column, Mapped
from wtforms import StringField, PasswordField, IntegerField, DecimalField, SelectField, TextAreaField, SubmitField
from model.base import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
from wtforms.validators import DataRequired, ValidationError, InputRequired, Length, EqualTo, Optional, NumberRange
from wtforms.fields.datetime import DateField
import enum

# Username and Password Checker
def invalid_credentials(form, field):
    username_entered = form.username.data
    password_entered = field.data

# Timezone
def london_time_now():
    return datetime.now(ZoneInfo("Europe/London"))

#Check if credentials are valid
    user = db.session.execute(db.select(User).filter_by(username=username_entered)).scalar_one_or_none()
    if user is None:
        raise ValidationError('Username or password is incorrect')
    elif not user.check_password(password_entered):
        raise ValidationError('Username or password is incorrect')

class TimeOfDay(enum.Enum):
    breakfast = "Breakfast"
    lunch     = "Lunch"
    dinner    = "Dinner"
    snack     = "Snack"

# class for the register form
class Register(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    def validate_username(form, field):
        user = db.session.execute(db.select(User).filter_by(username=field.data)).scalar_one_or_none()
        if user is not None:
            raise ValidationError('Username already exists, try another.')
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Re-enter your password', validators=[DataRequired(), EqualTo('password')])
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Surname', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Prefer Not To Say')] , validators=[DataRequired()])
    height = IntegerField('Height (cm)', validators=[DataRequired()])
    weight = DecimalField('Weight (kg)', places=1, validators=[DataRequired()])
    activity_level = SelectField('How active are you?', choices=[('none', "I don't go to the gym."), ('some', "I go 2 or 3 times a week to the gym."), ('alot', "I go more than 4 times a week to the gym.")], validators=[DataRequired()])
    goal = SelectField('What do you aim to achieve?', choices=[('lose', "I want to lose weight."), ('maintain', "I want to maintain my weight."), ('gain', "I want to gain weight.")])

#class for the login
class LoginForm(FlaskForm):
    username = StringField('username_label',
                           validators=[InputRequired(message="Username required")])
    password = StringField('password_label',
                           validators=[InputRequired(message="Password required"), invalid_credentials])

# class for registering user to the database
class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    firstname = db.Column(db.String(30), nullable=True)
    lastname = db.Column(db.String(30), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(6), nullable=True)
    height = db.Column(db.Integer, nullable=True)  # e.g., in cm
    weight = db.Column(db.Numeric(5, 1), nullable=True)  # e.g., 70.5 kg
    activity_level = db.Column(db.String(4), nullable=True)
    goal = db.Column(db.String(8), nullable=True)
    calorie_goal = db.Column(db.Integer, nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# class for form to log calories
class CalorieLogForm(FlaskForm):
    product = StringField('Food', validators=[DataRequired()])
    calories = IntegerField('Calories', validators=[DataRequired()])
    fat = DecimalField('Fat (g)', place=1, validators=[Optional()])
    saturated_fat = DecimalField('Saturated Fat (g)', place=1, validators=[Optional()])
    carbs = DecimalField('Carbohydrates (g)', places=1, validators=[Optional()])
    sugars = DecimalField('Sugars (g)', places=1, validators=[Optional()])
    protein = DecimalField('Protein (g)', places=1, validators=[Optional()])
    salt = DecimalField('Salt (g)', place=1, validators=[Optional()])
    fiber = DecimalField('Fiber (g)', place=1, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])

# class for moving the calorie log to the database
class CalorieLog(db.Model):
    __tablename__ = 'calorie_log'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product     = db.Column(db.String(100), nullable=False)
    time_of_day = db.Column(Enum(TimeOfDay), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    calories    = db.Column(db.Integer, nullable=False)
    fat         = db.Column(db.Numeric(8,1), nullable=True)
    saturated   = db.Column(db.Numeric(8,1), nullable=True)
    carbs       = db.Column(db.Numeric(8,1), nullable=True)
    sugars      = db.Column(db.Numeric(8,1), nullable=True)
    protein     = db.Column(db.Numeric(8,1), nullable=True)
    salt        = db.Column(db.Numeric(8,1), nullable=True)
    fiber       = db.Column(db.Numeric(8,1), nullable=True)

    notes       = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('calorie_logs', lazy=True))

class ExerciseLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    calories   = db.Column(db.Integer, nullable=False)
    notes      = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=london_time_now)

    user = db.relationship('User', backref=db.backref('exercise_logs', lazy=True))

class ProductList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String, nullable=True)
    product_size = db.Column(db.String, nullable=True)
    calories_kcal = db.Column(db.Numeric(8, 1), nullable=True)
    fat_g = db.Column(db.Numeric(8, 1), nullable=True)
    saturated_fat_g = db.Column(db.Numeric(8, 1), nullable=True)
    carbohydrates_g = db.Column(db.Numeric(8, 1), nullable=True)
    sugars_g = db.Column(db.Numeric(8, 1), nullable=True)
    protein_g = db.Column(db.Numeric(8, 1), nullable=True)
    salt_g = db.Column(db.Numeric(8, 1), nullable=True)
    fiber_g = db.Column(db.Numeric(8, 1), nullable=True)

class ExerciseLogForm(FlaskForm):
    calories = IntegerField('Calories Burned', validators=[DataRequired()])
    notes    = TextAreaField('Notes', validators=[Optional()])
    submit   = SubmitField('Add Exercise')

class AddFoodForm(FlaskForm):
    product     = StringField(
        'Food Name',
        validators=[DataRequired()],
        render_kw={'required': True}
    )
    size        = StringField(
        'Size',
        render_kw={'readonly': False}
    )
    time_of_day = SelectField(
        'When',
        choices=[(t.name, t.value) for t in TimeOfDay],
        validators=[DataRequired()],
        render_kw={'required': True}
    )
    quantity    = IntegerField(
        'Quantity (units)',
        default=1,
        validators=[DataRequired(), NumberRange(min=1)],
        render_kw={'required': True, 'min': 1}
    )
    calories    = IntegerField(
        'Calories (per unit)',
        validators=[DataRequired()],
        render_kw={'required': True}
    )
    fat         = DecimalField('Fat (g) per unit', places=1, validators=[Optional()])
    saturated   = DecimalField('Sat. Fat (g) per unit', places=1, validators=[Optional()])
    carbs       = DecimalField('Carbs (g) per unit', places=1, validators=[Optional()])
    sugars      = DecimalField('Sugars (g) per unit', places=1, validators=[Optional()])
    protein     = DecimalField('Protein (g) per unit', places=1, validators=[Optional()])
    salt        = DecimalField('Salt (g) per unit', places=1, validators=[Optional()])
    fiber       = DecimalField('Fiber (g) per unit', places=1, validators=[Optional()])
    notes       = TextAreaField('Notes', validators=[Optional()])
    submit      = SubmitField('Add Food')

class FindFoodForm(FlaskForm):
    code_lookup = StringField('Barcode', validators=[Optional()])
    submit      = SubmitField('Search')
