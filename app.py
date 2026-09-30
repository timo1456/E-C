import os
from pathlib import Path

from flask import Flask, Response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models.user import CartItem, Stock, User


BASE_DIR = Path(__file__).resolve().parent

# Vercel's deployed filesystem is read-only except for /tmp.
# SQLite is therefore kept in /tmp when running on Vercel.
# Locally, the database remains ./store.db.
if os.environ.get("VERCEL"):
    DATABASE_PATH = Path("/tmp/store.db")
else:
    DATABASE_PATH = BASE_DIR / "store.db"


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{DATABASE_PATH.as_posix()}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

db.init_app(app)


def initialize_database():
    """Create the SQLite tables and the first admin account."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(email="admin@store.com").first()
        if admin is None:
            admin = User(
                username="Admin",
                email="admin@store.com",
                password=generate_password_hash("admin"),
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()


initialize_database()


@app.get("/health")
def health():
    """Simple deployment health check."""
    return {"status": "ok", "database": "sqlite"}


@app.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("input-name", "").strip()
        email = request.form.get("input-email", "").strip().lower()
        password = request.form.get("input-pass", "")

        if not username or not email or not password:
            return render_template(
                "register.html",
                user_exist="Please fill in every field.",
            )

        if len(password) < 6:
            return render_template(
                "register.html",
                user_exist="Password must be at least 6 characters.",
            )

        if User.query.filter_by(username=username).first():
            return render_template(
                "register.html",
                user_exist="Username already exists.",
            )

        if User.query.filter_by(email=email).first():
            return render_template(
                "register.html",
                user_exist="Email already exists.",
            )

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role="customer",
        )
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            session["user"] = user.username
            session["role"] = user.role
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            invalid="Invalid email or password.",
        )

    return render_template("login.html")


def require_login():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return None


def require_admin():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    return None


@app.get("/dashboard")
def dashboard():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    if session.get("role") == "admin":
        return render_template("admin-dashboard.html", user=session["user"])

    search = request.args.get("search", "").strip()
    query = Stock.query

    if search:
        query = query.filter(Stock.pr_name.ilike(f"%{search}%"))

    products = query.order_by(db.func.random()).all()

    cart_count = (
        db.session.query(db.func.coalesce(db.func.sum(CartItem.quantity), 0))
        .filter(CartItem.user_id == session["user_id"])
        .scalar()
    )

    return render_template(
        "customer-dashboard.html",
        user=session["user"],
        products=products,
        search=search,
        cart_count=int(cart_count or 0),
    )


@app.get("/product-image/<int:product_id>")
def product_image(product_id):
    product = db.get_or_404(Stock, product_id)

    if not product.pr_img:
        return "", 404

    image = product.pr_img

    if image.startswith(b"\x89PNG"):
        mime_type = "image/png"
    elif image.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    elif image.startswith((b"GIF87a", b"GIF89a")):
        mime_type = "image/gif"
    elif image.startswith(b"RIFF") and image[8:12] == b"WEBP":
        mime_type = "image/webp"
    else:
        mime_type = "application/octet-stream"

    return Response(image, mimetype=mime_type)


@app.route("/add-items", methods=["GET", "POST"])
def add_items():
    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    if request.method == "POST":
        name = request.form.get("pr-name", "").strip()
        price_text = request.form.get("pr-price", "").strip()
        category = request.form.get("pr-category", "").strip()
        image = request.files.get("pr-img")

        if not name or not price_text or not category:
            return render_template(
                "add-items.html",
                error="Product name, price and category are required.",
            )

        try:
            price = int(float(price_text))
            if price < 0:
                raise ValueError
        except ValueError:
            return render_template(
                "add-items.html",
                error="Enter a valid non-negative price.",
            )

        stock = Stock(
            pr_name=name,
            pr_price=price,
            pr_category=category,
            pr_img=image.read() if image and image.filename else None,
        )

        db.session.add(stock)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add-items.html")


@app.post("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    if session.get("role") != "customer":
        return redirect(url_for("dashboard"))

    product = db.get_or_404(Stock, product_id)

    item = CartItem.query.filter_by(
        user_id=session["user_id"],
        product_id=product.id,
    ).first()

    if item:
        item.quantity += 1
    else:
        db.session.add(
            CartItem(
                user_id=session["user_id"],
                product_id=product.id,
                quantity=1,
            )
        )

    db.session.commit()
    return redirect(url_for("dashboard"))


@app.get("/cart")
def cart():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    if session.get("role") != "customer":
        return redirect(url_for("dashboard"))

    items = CartItem.query.filter_by(user_id=session["user_id"]).all()

    total = sum(
        item.product.pr_price * item.quantity
        for item in items
    )

    return render_template(
        "cart.html",
        cart_items=items,
        total=total,
        user=session["user"],
    )


def get_customer_cart_item(item_id):
    return CartItem.query.filter_by(
        id=item_id,
        user_id=session["user_id"],
    ).first_or_404()


@app.post("/cart/increase/<int:item_id>")
def increase_cart_item(item_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    if session.get("role") != "customer":
        return redirect(url_for("dashboard"))

    item = get_customer_cart_item(item_id)
    item.quantity += 1
    db.session.commit()

    return redirect(url_for("cart"))


@app.post("/cart/decrease/<int:item_id>")
def decrease_cart_item(item_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    if session.get("role") != "customer":
        return redirect(url_for("dashboard"))

    item = get_customer_cart_item(item_id)

    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)

    db.session.commit()
    return redirect(url_for("cart"))


@app.post("/cart/remove/<int:item_id>")
def remove_cart_item(item_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect

    if session.get("role") != "customer":
        return redirect(url_for("dashboard"))

    item = get_customer_cart_item(item_id)
    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("cart"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
