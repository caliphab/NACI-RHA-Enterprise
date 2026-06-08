from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, FloatField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from flask_wtf.file import FileAllowed, FileField

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class CheckoutForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    delivery_option = SelectField('Delivery Option', choices=[('standard', 'Standard Delivery'), ('express', 'Express Delivery')])
    payment_method = SelectField('Payment Method', choices=[
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Debit Card'),
        ('ussd', 'USSD'),
        ('mobile', 'Mobile Banking')
    ])

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number')
    message = TextAreaField('Message', validators=[DataRequired()])

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Selling Price (₦)', validators=[DataRequired(), NumberRange(min=0.01)])
    compare_price = FloatField('Compare at Price (₦)', validators=[NumberRange(min=0)])
    stock = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])
    sku = StringField('SKU', validators=[DataRequired(), Length(min=2, max=50)])
    brand = StringField('Brand', validators=[Length(max=100)])
    
    category_id = SelectField('Category', choices=[], coerce=int, validators=[DataRequired()])
    
    discount_percent = IntegerField('Discount Percentage (%)', validators=[NumberRange(min=0, max=100)], default=0)
    is_featured = BooleanField('Featured Product', default=False)
    is_bestseller = BooleanField('Best Seller', default=False)
    images = FileField('Product Images', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
    ], render_kw={"multiple": True})
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [("", "-- Select Category --")]