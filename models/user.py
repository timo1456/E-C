from extensions import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")


class Stock(db.Model):
    __tablename__ = "stock"

    id = db.Column(db.Integer, primary_key=True)
    pr_name = db.Column(db.String(150), nullable=False)
    pr_price = db.Column(db.Integer, nullable=False)
    pr_img = db.Column(db.LargeBinary, nullable=True)
    pr_category = db.Column(db.String(100), nullable=False)


class CartItem(db.Model):
    __tablename__ = "cart_item"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("stock.id"),
        nullable=False,
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship(
        "User",
        backref=db.backref("cart_items", lazy=True),
    )
    product = db.relationship(
        "Stock",
        backref=db.backref("cart_items", lazy=True),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "product_id",
            name="unique_user_product_cart",
        ),
    )
