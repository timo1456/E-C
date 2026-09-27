from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pr_name = db.Column(db.String(100), nullable=False)
    pr_price = db.Column(db.Integer, nullable=False)
    pr_img = db.Column(db.LargeBinary, nullable=True)
    pr_category = db.Column(db.String(100), nullable=False)


# ============================================================
# CART ITEM MODEL
# Stores the products currently in a customer's cart.
# A customer can have one cart row per product, with quantity
# increasing when the same product is added again.
# ============================================================
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship("User", backref=db.backref("cart_items", lazy=True))
    product = db.relationship("Stock", backref=db.backref("cart_items", lazy=True))

    # Prevent duplicate cart rows for the same customer/product pair.
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_user_product_cart"),
    )
