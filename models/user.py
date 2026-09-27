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
