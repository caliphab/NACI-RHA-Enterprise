import os
import random
import string
from werkzeug.utils import secure_filename
from models import db, Product
from datetime import datetime

def generate_order_number():
    return 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def save_uploaded_file(file, upload_folder):
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    if hasattr(file, 'filename'):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        return unique_filename
    else:
        raise ValueError(f"Invalid file object: {type(file)}")

def update_product_rating(product_id):
    from models import Review
    product = Product.query.get(product_id)
    if product:
        reviews = Review.query.filter_by(product_id=product_id).all()
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            product.rating = round(avg_rating, 1)
            product.rating_count = len(reviews)
            db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}
 