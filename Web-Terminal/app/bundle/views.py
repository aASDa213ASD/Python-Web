from datetime import datetime
from platform import machine as platform_machine
from platform import node as platform_node
from platform import processor as platform_proc
from platform import system as platform_sys
from platform import version as platform_ver
from re import compile as re_compile
from flask import redirect, render_template, request, session, url_for, make_response, flash
from flask_login import login_user, current_user, logout_user, login_required
from .forms import FeedbackForm, LoginForm, ChangePasswordForm, TODOForm, RegisterForm, UpdateAccountForm
from secrets import token_hex
from app import app
from app import bcrypt
from app.bundle.handlers import post_handle
from app.bundle.models import db, User, Feedback, Todo
from PIL import Image
import os

@app.after_request
def update_last_seen(response):
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error while updating user last seen: {str(e)}", "danger")
    return response

""" Pfp helper function"""
def save_picture(form_pfp):
    random_hex = token_hex(8)
    f_name, f_ext = os.path.splitext(form_pfp.filename)
    pfp_fn = random_hex + f_ext
    pfp_path = os.path.join(app.root_path, 'static/images/pfps', pfp_fn)
    image = Image.open(form_pfp)
    image.thumbnail((360, 360))
    image.save(pfp_path)
    return pfp_fn
    #form_pfp.save(pfp_path)
    #return pfp_fn

""" Render helper function """
def render(template: str, **kwargs):
    return render_template(template, user=session.get("user"), **kwargs)

""" Cookies block """
@app.route("/setcookie", methods=["GET", "POST"])
def set_cookie():
    """ Deprecated, use LoginManager instead """
    if request.method == "POST" and (handle := post_handle()):
        return handle
    
    key = request.args.get("key")
    value = request.args.get("value")
    response = make_response(redirect(url_for("whoami")))

    if session.get("user"):
        if key and value:
            response.set_cookie(key=key, value=value)
    else:
        return render_template(
            "exceptions/permissions.html",
            user=session.get("user"), route=request.path,
            exception="You don't have enough permissions to execute this command."
        )
    return response

@app.route('/wipecookie', methods=["GET", "POST"])
def wipe_cookie():
    """ Deprecated, use LoginManager instead """
    if request.method == "POST" and (handle := post_handle()):
        return handle

    key = request.args.get("key")
    response = make_response(redirect(url_for("whoami")))
    
    if session.get("user"):
        if key:
            response.delete_cookie(key)
        else:
            cookie_keys = request.cookies.keys()
            for key in cookie_keys:
                response.delete_cookie(key)
    else:
        return render_template(
            "exceptions/permissions.html",
            user=session.get("user"), route=request.path,
            exception="You don't have enough permissions to execute this command."
        )
    return response

def list_folders():
    return render("information/list_folders.html")

""" Information block """
@app.route("/ls", methods=["GET"])
def list_folders():
    return render("information/list_folders.html")

@app.route("/help", methods=["GET"])
def help():
    return render("information/help.html")

@app.route("/whois", methods=["GET"])
def whois():
    return render("information/whois.html")

@app.route("/projects", methods=["GET"])
def projects():
    return render("information/projects.html")

""" Route block """
@app.route('/skills', methods=["GET", "POST"])
@app.route('/skills/<int:id>', methods=["GET", "POST"])
def skills(id=None):
    if request.method == "POST" and (handle := post_handle()):
        return handle
    
    skills = [
        {"name": "Assembly", "description": "Reverse Engineering"},
        {"name": "C++", "description": "Internal Domain"},
        {"name": "Python", "description": "Botnet Producer"},
        {"name": "Java", "description": "Stuff Manager"}
    ]

    if id or id == 0:
        skill = None
        try:
            skill = skills[id]
        except Exception:
            pass
        if skill:
            return render("routes/skill_detail.html", route=request.path, skill=skill)

    return render("routes/skill_list.html", route=request.path, skills=skills)

@app.route("/system", methods=["GET", "POST"])
def system():
    if request.method == "POST" and (handle := post_handle()):
        return handle
    
    pattern = re_compile(r'(Mozilla/5.0 \(.*\)) (AppleWebKit/.* \(.*\)) (Chrome/.* Safari/.*)')
    platform, webkit, browser = pattern.match(request.headers.get('User-Agent')).groups() 

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os_info = {
        "System": platform_sys(),
        "Node": platform_node(),
        "Version": platform_ver(),
        "Machine": platform_machine(),
        "Processor": platform_proc(),
    }

    return render(
        "routes/system.html", 
        route=request.path,
        ua_platform=platform, ua_webkit=webkit, ua_browser=browser,
        os_info=os_info, current_time=current_time
    )

@app.route("/about", methods=["GET", "POST"])
def about():
    if request.method == "POST" and (handle := post_handle()):
        return handle
    return render("routes/about.html", route=request.path)

@app.route("/gamehacking", methods=["GET", "POST"])
def gamehacking():
    if request.method == "POST" and (handle := post_handle()):
        return handle
    return render("routes/gamehacking.html", route=request.path)

@app.route("/gallery", methods=["GET", "POST"])
def gallery():
    if request.method == "POST" and (handle := post_handle()):
        return handle
    return render("routes/gallery.html", route=request.path)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("whoami"))
    
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        new_user = User(username=username, password=password)

        db.session.add(new_user)
        db.session.commit()
        flash("Your account has been created.", category="flash-success")

        return redirect(url_for("login"))
    
    return render("routes/register.html", route=request.path, form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("whoami"))
        
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember_flag = form.remember.data
        user = User.query.filter_by(username=username).first()
        if user and user.validate_pwd(password):
            if remember_flag:
                login_user(user, remember_flag)
                #session['user_id'] = user.id
                #session['user'] = user.username
                #session['remember'] = remember_flag
                return redirect(url_for("whoami"))
            else:
                return redirect(url_for("root"))
        else:
            flash("Authentication failure", "danger")
    return render("routes/login.html", route=request.path, form=form)

@app.route("/whoami", methods=["GET", "POST"])
@login_required
def whoami():
    form = UpdateAccountForm()
    form.username.default = current_user.username
    form.bio.default = current_user.bio

    if form.validate_on_submit():
        if form.pfp.data:
            pfp_file = save_picture(form.pfp.data)
            current_user.pfp = pfp_file
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        db.session.commit()
        return redirect(url_for("whoami"))
    
    if current_user.is_authenticated:
        """ Deprecated request.cookies, use LoginManager instead """
        form.process()
        return render("routes/whoami.html", route=request.path, cookies=request.cookies, form=form)
    
    return redirect(url_for("login"))

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = Feedback(
            username=form.username.data, 
            feedback=form.feedback.data
        )

        db.session.add(feedback)
        db.session.commit()

        flash('Feedback submitted successfully!')
        return redirect(url_for("feedback"))
    
    return render("routes/feedback.html", route=request.path, cookies=request.cookies, form=form, feedback_list=reversed(db.session.query(Feedback).all()))
    
@app.route("/exit", methods=["GET", "POST"])
def exit():
    try:
        logout_user()
    except Exception:
        pass
    return redirect(url_for("root"))

@app.route("/passwd", methods=["GET", "POST"])
def passwd():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        new_pwd = form.password.data
        confirm_pwd = form.confirm_password.data
        user = User.query.filter_by(username=session.get("user")).first()
        if user:
            new_pwd = bcrypt.generate_password_hash(new_pwd).decode('utf-8')
            user.password = new_pwd

            db.session.add(user)
            db.session.commit()

            session.pop("user") # <- Log him out
            return redirect(url_for("login"))
    
    return render("routes/passwd.html", route=request.path, form=form)

@app.route("/todo", methods=["GET", "POST"])
@login_required
def todo():
    form = TODOForm()
    if current_user.is_authenticated:
        user = User.query.filter_by(username=session.get("user")).first()
        return render("routes/todo.html", route=request.path, form=form, todo_list=reversed(db.session.query(Todo).filter_by(user_id=current_user.id).all()))

    if form.validate_on_submit():
        user = User.query.filter_by(username=session.get("user")).first()
        if user:
            title = form.title.data
            description = form.description.data
            due_date = form.due_date.data
            todo = Todo(user_id=user.id, title=title, description=description, due_date=due_date, status=False)
            db.session.add(todo)
            db.session.commit()
            return redirect(url_for("todo"))

    return redirect(url_for("login"))

@app.route("/todo_status/<int:id>")
def todo_status(id):
    todo = Todo.query.get(id)
    todo.status = not todo.status
    db.session.commit()
    return redirect(url_for("todo"))

@app.route("/todo_remove/<int:id>")
def todo_remove(id):
    db.session.delete(Todo.query.get(id))
    db.session.commit()
    return redirect(url_for("todo"))

@app.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST" and (handle := post_handle()):
        return handle
    registered_users = User.query.all()
    #registered_users = [username for (username,) in User.query.with_entities(User.username).all()]
    return render("routes/users.html", route=request.path, user_list=registered_users)

@app.route("/", methods=["GET", "POST"])
def root():
    if request.method == "POST" and (handle := post_handle()):
        return handle
    return render("routes/root.html", route="~")