import os
import random
import string
import uuid
from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy.exc import InvalidRequestError

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

def generate_verification_code():
    return ''.join(random.choice(string.digits) for _ in range(6))

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    user_id = db.Column(db.String(64), index=True, unique=True)
    phone_number = db.Column(db.String(15))
    password = db.Column(db.String(128))
    authenticated = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def send_verification_code(self):
        verification_code = generate_verification_code()
        client.messages.create(
            body=f"Your verification code is: {verification_code}",
            from_=TWILIO_PHONE_NUMBER,
            to=self.phone_number
        )
        return verification_code


class RegistrationForm(FlaskForm):
    user_id = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])


class LoginForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    submit = SubmitField('Submit')


class VerificationCodeForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[DataRequired()])
    submit = SubmitField('Submit')


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(user_id)
    except (InvalidRequestError, ValueError):
        return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(user_id=form.user_id.data).first()
        if user:
            print('Username is already taken')
            return redirect(url_for('register'))

        new_user = User(user_id=form.user_id.data, phone_number=form.phone_number.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        print('Registration successful. Please check your phone for the verification code.')
        return redirect(url_for('verify', user_id=new_user.user_id))

    return render_template('register.html', title='Register', form=form)


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        user_code = request.form.get('verification_code')
        if user_code == str(session.get('verification_code')):
            return redirect(url_for('index'))
        else:
            print("Wrong verification code")
    else:
        form = VerificationCodeForm()
        return render_template('verify.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        phone_number = form.phone_number.data
        user = User.query.filter_by(phone_number=phone_number).first()
        if user is None:
            print('No user with this phone number found')
            return redirect(url_for('login'))

        session['phone_number'] = phone_number

        verification_code = user.send_verification_code()
        session['verification_code'] = verification_code

        return redirect(url_for('verify'))

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
def index():
    return render_template('index.html', title='Home')


if __name__ == '__main__':
    app.run(debug=True)

