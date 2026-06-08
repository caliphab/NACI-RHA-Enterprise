from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User, Product, Category, Order, OrderItem, Wishlist, Review, ContactMessage, ProductImage
from forms import LoginForm, RegistrationForm, CheckoutForm, ContactForm, ProductForm
from utils import allowed_file, generate_order_number, save_uploaded_file, update_product_rating
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    featured_products = Product.query.filter_by(is_featured=True).limit(8).all()
    bestsellers = Product.query.filter_by(is_bestseller=True).limit(8).all()
    new_arrivals = Product.query.filter_by(is_new=True).limit(8).all()
    categories = Category.query.filter_by(parent_id=None).limit(6).all()
    
    return render_template('index.html', 
                         featured_products=featured_products,
                         bestsellers=bestsellers,
                         new_arrivals=new_arrivals,
                         categories=categories)

@app.route('/shop')
def shop():
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort = request.args.get('sort', 'newest')
    brand = request.args.get('brand', '')
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    if min_price:
        query = query.filter(Product.price >= min_price)
    if max_price:
        query = query.filter(Product.price <= max_price)
    if brand:
        query = query.filter_by(brand=brand)
    
    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'rating':
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    
    products = query.all()
    categories = Category.query.all()
    brands = db.session.query(Product.brand).distinct().all()
    
    return render_template('shop.html', products=products, categories=categories, 
                         brands=brands, search=search)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter_by(category_id=product.category_id)\
                                   .filter(Product.id != product_id).limit(4).all()
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    in_wishlist = False
    
    if current_user.is_authenticated:
        in_wishlist = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first() is not None
    
    return render_template('product_detail.html', product=product, related_products=related_products,
                         reviews=reviews, in_wishlist=in_wishlist)

@app.route('/cart')
def cart():
    cart_items = session.get('cart', {})
    products = []
    total = 0
    
    for product_id, quantity in cart_items.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.final_price * quantity
            total += item_total
            products.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
    
    return render_template('cart.html', products=products, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    session['cart'] = cart
    
    flash('Product added to cart!', 'success')
    return redirect(request.referrer or url_for('shop'))

@app.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 0))
    cart = session.get('cart', {})
    
    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = quantity
    
    session['cart'] = cart
    flash('Cart updated!', 'success')
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    flash('Product removed from cart', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    form = CheckoutForm()
    cart_items = session.get('cart', {})
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('shop'))
    
    products = []
    subtotal = 0
    
    for product_id, quantity in cart_items.items():
        product = Product.query.get(int(product_id))
        if product and product.in_stock:
            item_total = product.final_price * quantity
            subtotal += item_total
            products.append({'product': product, 'quantity': quantity, 'total': item_total})
    
    delivery_fee = 1500 if form.delivery_option.data == 'express' else 500
    grand_total = subtotal + delivery_fee
    
    if form.validate_on_submit():
        order = Order(
            order_number=generate_order_number(),
            user_id=current_user.id,
            total_amount=subtotal,
            delivery_fee=delivery_fee,
            grand_total=grand_total,
            delivery_address=f"{form.address.data}, {form.city.data}, {form.state.data}",
            delivery_phone=form.phone.data,
            delivery_option=form.delivery_option.data,
            payment_method=form.payment_method.data
        )
        
        db.session.add(order)
        db.session.flush()
        
        for item in products:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price=item['product'].final_price,
                total=item['total']
            )
            db.session.add(order_item)
            
            item['product'].stock -= item['quantity']
        
        db.session.commit()
        session.pop('cart', None)
        
        flash(f'Order placed successfully! Order #: {order.order_number}', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('checkout.html', form=form, products=products, 
                         subtotal=subtotal, delivery_fee=delivery_fee, grand_total=grand_total)

@app.route('/dashboard')
@login_required
def dashboard():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
    
    return render_template('dashboard.html', orders=orders, wishlist_items=wishlist_items)

@app.route('/wishlist/add/<int:product_id>')
@login_required
def add_to_wishlist(product_id):
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not existing:
        wishlist = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(wishlist)
        db.session.commit()
        flash('Added to wishlist!', 'success')
    else:
        flash('Product already in wishlist', 'info')
    
    return redirect(request.referrer or url_for('shop'))

@app.route('/wishlist/remove/<int:product_id>')
@login_required
def remove_from_wishlist(product_id):
    Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
    db.session.commit()
    flash('Removed from wishlist', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_all_to_cart', methods=['POST'])
@login_required
def add_all_to_cart():
    wishlist_entries = Wishlist.query.filter_by(user_id=current_user.id).all()
    cart = session.get('cart', {})
    added_count = 0
    
    for entry in wishlist_entries:
        product = Product.query.get(entry.product_id)
        if product and product.in_stock:
            product_id = str(product.id)
            cart[product_id] = cart.get(product_id, 0) + 1
            added_count += 1
    
    session['cart'] = cart
    flash(f'{added_count} items added to your cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/add_review/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '')
    
    if rating >= 1 and rating <= 5:
        review = Review(user_id=current_user.id, product_id=product_id, rating=rating, comment=comment)
        db.session.add(review)
        db.session.commit()
        update_product_rating(product_id)
        flash('Review added!', 'success')
    
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/track_order/<order_number>')
@login_required
def track_order(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template('order_tracking.html', order=order)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            message=form.message.data
        )
        db.session.add(message)
        db.session.commit()
        flash('Message sent! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            email=form.email.data,
            password_hash=hashed_password,
            full_name=form.full_name.data,
            phone=form.phone.data
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('cart', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('index'))
    
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_products = Product.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin_dashboard.html', total_orders=total_orders,
                         total_users=total_users, total_products=total_products,
                         pending_orders=pending_orders, recent_orders=recent_orders)

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    form = ProductForm()
    categories = Category.query.order_by(Category.name).all()

    if categories:
        form.category_id.choices = [(0, '-- Select Category --')] + [(cat.id, cat.name) for cat in categories]
    else:
        form.category_id.choices = [
            ("", "-- Select Category --"),
            ("1", "📱 Electronics"),
            ("2", "👕 Fashion & Accessories"),
            ("3", "📚 Books & Media"),
            ("4", "🏠 Home Appliances"),
            ("5", "💄 Beauty Products"),
            ("6", "🍳 Kitchen Equipment"),
            ("7", "📱 Phones & Accessories"),
            ("8", "💻 Computer Accessories"),
            ("9", "🧸 Children's Products")
        ]
    
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            compare_price=form.compare_price.data,
            stock=form.stock.data,
            sku=form.sku.data,
            brand=form.brand.data,
            category_id=form.category_id.data,
            is_featured=form.is_featured.data,
            is_bestseller=form.is_bestseller.data,
            discount_percent=form.discount_percent.data
        )
        
        db.session.add(product)
        db.session.commit()
        
        if form.images.data:
            uploaded_files = form.images.data
            
            # Check if it's a list or single file
            if not isinstance(uploaded_files, list):
                uploaded_files = [uploaded_files]
            
            for index, img in enumerate(uploaded_files):
                if img and hasattr(img, 'filename') and img.filename:
                    if allowed_file(img.filename):
                        try:
                            filename = save_uploaded_file(img, app.config['UPLOAD_FOLDER'])
                            is_main = (index == 0)
                            product_image = ProductImage(
                                product_id=product.id, 
                                image_url=filename, 
                                is_main=is_main
                            )
                            db.session.add(product_image)
                        except Exception as e:
                            print(f"Error saving image: {e}")
                            flash(f'Error saving image {img.filename}: {str(e)}', 'danger')
                    else:
                        flash(f'File {img.filename} is not an allowed image type', 'warning')
        
        db.session.commit()
        flash(f'Product "{product.name}" added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_product_form.html', form=form, categories=categories, title='Add Product')

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>/update', methods=['POST'])
@login_required
def admin_update_order(order_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get('status')
    db.session.commit()
    flash('Order status updated!', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/messages')
@login_required
def admin_messages():
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('index'))
    
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin_messages.html', messages=messages, now=datetime.utcnow())

@app.route('/api/message/<int:message_id>')
@login_required
def get_message(message_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    message = ContactMessage.query.get_or_404(message_id)
    return jsonify({
        'id': message.id,
        'name': message.name,
        'email': message.email,
        'phone': message.phone,
        'message': message.message,
        'created_at': message.created_at.isoformat()
    })

@app.route('/admin/message/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    message = ContactMessage.query.get_or_404(message_id)
    message.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/message/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    message = ContactMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/messages/mark-read', methods=['POST'])
@login_required
def mark_messages_read():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    message_ids = data.get('message_ids', [])
    
    ContactMessage.query.filter(ContactMessage.id.in_(message_ids)).update(
        {'is_read': True}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/messages/delete-multiple', methods=['POST'])
@login_required
def delete_multiple_messages():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    message_ids = data.get('message_ids', [])
    
    ContactMessage.query.filter(ContactMessage.id.in_(message_ids)).delete(
        synchronize_session=False
    )
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/messages/mark-all-read', methods=['POST'])
@login_required
def mark_all_messages_read():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    ContactMessage.query.update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/messages/delete-all', methods=['POST'])
@login_required
def delete_all_messages():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    ContactMessage.query.delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/message/reply', methods=['POST'])
@login_required
def reply_to_message():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    email = data.get('email')
    subject = data.get('subject')
    message = data.get('message')
    
    # Code to integrate with an email service (SMTP, SendGrid, etc.)
    
    return jsonify({'success': True, 'message': 'Reply sent successfully'})

# Api endpoints
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    products = Product.query.filter(Product.name.contains(query)).limit(10).all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': p.price} for p in products])

@app.route('/api/cart_count')
def api_cart_count():
    cart = session.get('cart', {})
    count = sum(cart.values())
    return jsonify({'count': count})

@app.route('/wishlist')
@login_required
def wishlist():
    wishlist_entries = Wishlist.query.filter_by(user_id=current_user.id).all()
    
    wishlist_items = []
    for entry in wishlist_entries:
        product = Product.query.get(entry.product_id)
        if product:
            wishlist_items.append({
                'id': entry.id,
                'product': product,
                'created_at': entry.created_at
            })
    
    suggested_products = Product.query.filter_by(is_bestseller=True).limit(4).all()
    if not suggested_products:
        suggested_products = Product.query.filter_by(is_featured=True).limit(4).all()
    if not suggested_products:
        suggested_products = Product.query.limit(4).all()
    
    return render_template('wishlist.html', 
                         wishlist_items=wishlist_items,
                         products=suggested_products)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.full_name = request.form.get('full_name')
    current_user.phone = request.form.get('phone')
    current_user.address = request.form.get('address')
    current_user.city = request.form.get('city')
    current_user.state = request.form.get('state')
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    # email management program here
    flash('Subscribed successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    categories = Category.query.order_by(Category.name).all()
    form.category_id.choices = [(cat.id, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.compare_price = form.compare_price.data
        product.stock = form.stock.data
        product.sku = form.sku.data
        product.brand = form.brand.data
        product.category_id = form.category_id.data
        product.is_featured = form.is_featured.data
        product.is_bestseller = form.is_bestseller.data
        product.discount_percent = form.discount_percent.data
        
        db.session.commit()
        
        if form.images.data:
            for img in form.images.data:
                if img and allowed_file(img.filename):
                    filename = save_uploaded_file(img, app.config['UPLOAD_FOLDER'])
                    product_image = ProductImage(product_id=product.id, image_url=filename, is_main=False)
                    db.session.add(product_image)
            
            db.session.commit()
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_product_form.html', form=form, categories=categories, title='Edit Product')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)