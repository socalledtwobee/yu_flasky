from flask import Flask, render_template, session, redirect, url_for, flash
from flask_script import Manager, Shell
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import Form
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate, MigrateCommand
from flask_mail import Message, Mail
from threading import Thread

basedir = os.path.abspath(os.path.dirname(__file__))

# 环境配置
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
# 邮件配置
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_MAIL_SENDER'] = 'Flasky Admin <809390770@qq.com>'

# 初始化全局重要对象
db = SQLAlchemy(app=app)
manager = Manager(app=app)
bootstrap = Bootstrap(app=app)
moment = Moment(app=app)
migrate = Migrate(app=app, db=db)
mail = Mail(app=app)


# 表单类
class NameForm(Form):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


# ORM
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role {role.name}>'.format(role=self)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User {user.username}>'.format(user=self)


# 路由函数
# 异常捕获函数
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# 视图函数
@app.route('/', methods=['GET', 'POST'])
def index():
    # name = None
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        # old_name = session.get('name')
        # if old_name is not None and old_name != form.name.data:
        #     flash('Looks like you changed your name!')
        # name = form.name.data
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
            if app.config['FLASKY_ADMIN']:
                send_mail(to=app.config['FLASKY_ADMIN'], subject='New User', template='mail/new_user', user=user)
        else:
            session['known'] = True
        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('index'))
    return render_template('index.html', form=form, name=session.get('name'), known=session.get('known', False))


# 为Shell导入上下文
def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)


# 设置启动命令
manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


# 发送邮件
def send_async_email(_app, msg):
    with _app.app_context():
        mail.send(msg)


def send_mail(to, subject, template, **kwargs):
    print('starting send mail')
    msg = Message(subject=app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject, sender=app.config['FLASKY_MAIL_SENDER'],
                  recipients=[to])
    msg.body = render_template(template_name_or_list=template + '.txt', **kwargs)
    msg.html = render_template(template_name_or_list=template + '.html', **kwargs)
    mail.send(msg)
    thr = Thread(target=send_async_email, args=(app, msg))
    thr.start()
    return thr


if __name__ == '__main__':
    manager.run()
