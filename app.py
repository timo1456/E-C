import os
from flask import request
from flask import Flask, redirect, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text
from extensions import db
from models.user import (
    User,
    Stock,
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "store-name-name"
)


basedir = os.path.abspath(
    os.path.dirname(__file__)
)

database_path = os.path.join(basedir, "store.db")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + database_path.replace(os.sep, "/")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():

    db.create_all()

    admin = User.query.filter_by(
        username="Admin"
    ).first()
    
    if not admin:
    
        admin = User(
            username="Admin",
            password=generate_password_hash(
                "admin"
            ),
            role="admin",
            email="admin@store.com"
            )
    
        db.session.add(admin)
        db.session.commit()



@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("input-name", "").strip()
        email = request.form.get("input-email", "").strip()
        password = request.form.get("input-pass", "")

        existing_username = User.query.filter_by(
            username=username
        ).first()

        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_username:
            return render_template(
                "register.html",
                user_exist="Username already exists"
            )

        if existing_email:
            return render_template(
                "register.html",
                user_exist="Email already exists"
            )
        
        user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    role = "customer"
                )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template(
        "register.html"
    )

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password 
        ):
            session.clear()
            session["user"] = user.username
            session["role"] = user.role
            session["user_id"] = user.id
            
            return redirect("/dashboard")
        

        return render_template(
            "login.html",
            invalid="Invalid email or password"
        )
    return render_template ("login.html")

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")
    
    if session["role"] == "admin":

        return render_template(
            "admin-dashboard.html",
            user=session["user"]
        )    
    
    if session["role"] == "customer":
    
        return render_template(
            "customer-dashboard.html",
            user=session["user"],

        )

    return "Error"


@app.route("/add-items", methods=["GET", "POST"])
def add_items():
    if request.method == "POST":
        pr_name = request.form.get("pr-name")
        pr_img = request.files.get("pr-img")
        pr_price = request.form.get("pr-price")
        pr_category = request.form.get("pr-category")

        stock = Stock(
            pr_name = pr_name,
            pr_price = pr_price,
            pr_category = pr_category,
            pr_img = pr_img.read()
        )

        db.session.add(stock)
        db.session.commit()

        return render_template(
            "add-items.html"
        )

    return render_template(
        "add-items.html"
    )    

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")








if __name__ == "__main__":
    app.run(debug=True)