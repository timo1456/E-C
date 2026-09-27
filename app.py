import os
from flask import request, Response
from flask import Flask, redirect, render_template, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models.user import (
    User,
    Stock,
    CartItem,
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
            password=generate_password_hash("admin"),
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

        existing_username = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()

        if existing_username:
            return render_template("register.html", user_exist="Username already exists")

        if existing_email:
            return render_template("register.html", user_exist="Email already exists")

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role="customer"
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.clear()
            session["user"] = user.username
            session["role"] = user.role
            session["user_id"] = user.id
            return redirect("/dashboard")

        return render_template("login.html", invalid="Invalid email or password")

    return render_template("login.html")


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
        # ============================================================
        # CUSTOMER PRODUCT DISPLAY
        # Gets products saved by the admin from the database.
        # order_by(db.func.random()) is intentional for now so that
        # products appear in a random order on each dashboard visit.
        # The search value is also read from the URL so customers can
        # search for a particular product.
        # ============================================================
        search = request.args.get("search", "").strip()

        products_query = Stock.query

        if search:
            products_query = products_query.filter(
                Stock.pr_name.ilike(f"%{search}%")
            )

        products = products_query.order_by(db.func.random()).all()

        # ============================================================
        # CART COUNT
        # Shows the total number of units currently in the customer's
        # cart. This is displayed in the dashboard/cart link.
        # ============================================================
        cart_count = db.session.query(
            db.func.coalesce(db.func.sum(CartItem.quantity), 0)
        ).filter(
            CartItem.user_id == session["user_id"]
        ).scalar()

        return render_template(
            "customer-dashboard.html",
            user=session["user"],
            products=products,
            search=search,
            cart_count=int(cart_count or 0)
        )

    return "Error"


@app.route("/product-image/<int:product_id>")
def product_image(product_id):
    # ============================================================
    # PRODUCT IMAGE ROUTE
    # Product images are stored as binary data in the database.
    # This route sends the saved image back to the browser so the
    # customer dashboard can display it.
    # ============================================================
    product = db.get_or_404(Stock, product_id)

    if not product.pr_img:
        return "", 404

    # Detect common uploaded image formats from their file signatures.
    # This keeps PNG/GIF/WEBP uploads from being incorrectly sent as JPEG.
    if product.pr_img.startswith(b"\\x89PNG"):
        mime_type = "image/png"
    elif product.pr_img.startswith(b"\\xff\\xd8\\xff"):
        mime_type = "image/jpeg"
    elif product.pr_img.startswith((b"GIF87a", b"GIF89a")):
        mime_type = "image/gif"
    elif product.pr_img.startswith(b"RIFF") and product.pr_img[8:12] == b"WEBP":
        mime_type = "image/webp"
    else:
        mime_type = "application/octet-stream"

    return Response(product.pr_img, mimetype=mime_type)


@app.route("/add-items", methods=["GET", "POST"])
def add_items():
    if request.method == "POST":
        pr_name = request.form.get("pr-name")
        pr_img = request.files.get("pr-img")
        pr_price = request.form.get("pr-price")
        pr_category = request.form.get("pr-category")

        stock = Stock(
            pr_name=pr_name,
            pr_price=pr_price,
            pr_category=pr_category,
            pr_img=pr_img.read() if pr_img else None
        )

        db.session.add(stock)
        db.session.commit()

        return render_template("add-items.html")

    return render_template("add-items.html")


@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    # ============================================================
    # ADD TO CART
    # Adds a product to the logged-in customer's cart.
    # If that product is already in the cart, only its quantity is
    # increased instead of creating another cart row.
    # ============================================================
    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "customer":
        return redirect("/dashboard")

    product = db.get_or_404(Stock, product_id)

    cart_item = CartItem.query.filter_by(
        user_id=session["user_id"],
        product_id=product.id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(
            user_id=session["user_id"],
            product_id=product.id,
            quantity=1
        )
        db.session.add(cart_item)

    db.session.commit()

    return redirect(url_for("dashboard"))


@app.route("/cart")
def cart():
    # ============================================================
    # CART PAGE
    # Retrieves all cart items belonging to the currently logged-in
    # customer and calculates each subtotal and the overall total.
    # ============================================================
    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "customer":
        return redirect("/dashboard")

    cart_items = CartItem.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total = sum(
        item.product.pr_price * item.quantity
        for item in cart_items
    )

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total,
        user=session["user"]
    )


@app.route("/cart/increase/<int:item_id>", methods=["POST"])
def increase_cart_item(item_id):
    # ============================================================
    # INCREASE CART QUANTITY
    # Increases the quantity of one existing cart item by one.
    # ============================================================
    if "user" not in session or session.get("role") != "customer":
        return redirect("/login")

    item = CartItem.query.filter_by(
        id=item_id,
        user_id=session["user_id"]
    ).first_or_404()

    item.quantity += 1
    db.session.commit()

    return redirect(url_for("cart"))


@app.route("/cart/decrease/<int:item_id>", methods=["POST"])
def decrease_cart_item(item_id):
    # ============================================================
    # DECREASE CART QUANTITY
    # Decreases quantity by one. When quantity reaches zero, the
    # cart item is removed completely.
    # ============================================================
    if "user" not in session or session.get("role") != "customer":
        return redirect("/login")

    item = CartItem.query.filter_by(
        id=item_id,
        user_id=session["user_id"]
    ).first_or_404()

    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)

    db.session.commit()

    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
def remove_cart_item(item_id):
    # ============================================================
    # REMOVE FROM CART
    # Completely removes the selected product from the customer's
    # cart regardless of its current quantity.
    # ============================================================
    if "user" not in session or session.get("role") != "customer":
        return redirect("/login")

    item = CartItem.query.filter_by(
        id=item_id,
        user_id=session["user_id"]
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("cart"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
