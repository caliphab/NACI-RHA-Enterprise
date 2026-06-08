from app import app
from models import db, User, Category
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

def init_database():
    with app.app_context():
        db.create_all()
        
        admin = User.query.filter_by(email='admin@nac-heerah.com').first()
        if not admin:
            admin = User(
                email='admin@nac-heerah.com',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                full_name='Admin User',
                phone='+2348000000000',
                is_admin=True
            )
            db.session.add(admin)
        
        categories = [
            {'name': 'Electronics', 'description': 'Latest electronic gadgets and devices'},
            {'name': 'Home Appliances', 'description': 'Quality home appliances'},
            {'name': 'Fashion & Accessories', 'description': 'Trendy fashion items'},
            {'name': 'Beauty Products', 'description': 'Premium beauty and skincare'},
            {'name': 'Kitchen Equipment', 'description': 'Professional kitchen tools'},
            {'name': 'Phones & Accessories', 'description': 'Latest smartphones and accessories'},
            {'name': 'Computer Accessories', 'description': 'Computer peripherals and accessories'},
            {'name': "Children's Products", 'description': 'Toys and children essentials'}
        ]
        
        for cat_data in categories:
            category = Category.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = Category(name=cat_data['name'], description=cat_data['description'])
                db.session.add(category)
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()