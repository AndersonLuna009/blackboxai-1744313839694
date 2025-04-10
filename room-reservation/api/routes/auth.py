from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from api.models import db, User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

auth_bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message="Email é obrigatório"),
        Email(message="Por favor, insira um endereço de email válido")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Senha é obrigatória")
    ])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Nome de usuário é obrigatório"),
        Length(min=3, max=50, message="O nome de usuário deve ter entre 3 e 50 caracteres")
    ])
    email = EmailField('Email', validators=[
        DataRequired(message="Email é obrigatório"),
        Email(message="Por favor, insira um endereço de email válido")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Senha é obrigatória"),
        Length(min=6, message="A senha deve ter pelo menos 6 caracteres")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Confirmação de senha é obrigatória"),
        EqualTo('password', message='As senhas devem ser iguais')
    ])
    terms = BooleanField('Terms', validators=[
        DataRequired(message="Você deve aceitar os termos e condições")
    ])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Este nome de usuário já está em uso')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Este email já está registrado')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data)
            )
            db.session.add(user)
            db.session.commit()
            flash('Registro realizado com sucesso! Por favor, faça login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Ocorreu um erro ao registrar. Por favor, tente novamente.', 'error')
            print(f"Error during registration: {str(e)}")
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Login realizado com sucesso!', 'success')
            return redirect(next_page if next_page else url_for('index'))
        flash('Email ou senha inválidos', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')
