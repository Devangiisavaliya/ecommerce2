from flask import Flask, render_template, request, redirect, session,flash
from flask_mysqldb import MySQL
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from functools import wraps
from flask import session, redirect, url_for
from flask import flash

app = Flask(__name__)

# SECRET KEY     
app.secret_key = "admin123"

# MYSQL CONFIG     
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ecommerce2'

mysql = MySQL(app)                                                        

# MAIL CONFIG     
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'devangisavaliya3@gmail.com'
app.config['MAIL_PASSWORD'] = 'yvupxupnpieokvnp'

mail = Mail(app)

def send_invoice_email(user_email, user_name, items):

    total = 0

    body = f"""
    <h2>Hello {user_name},</h2>

    <p>Thank you for your purchase </p>

    <h3>Your Invoice Details</h3>

    <table border="1" cellpadding="10" cellspacing="0" width="100%">
        <tr>
            <th>Product</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Subtotal</th>
        </tr>
    """

    for item in items:

        name = item[0]
        qty = item[1]
        price = item[2]

        subtotal = float(qty) * float(price)
        total += subtotal

        body += f"""
        <tr>
            <td>{name}</td>
            <td>{qty}</td>
            <td>₹{price}</td>
            <td>₹{subtotal}</td>
        </tr>
        """

    body += f"""
    </table>

    <br>

    <h2>Total Amount : ₹{total}</h2>

    <p>
        Your order has been placed successfully ✅
    </p>

    <p>
        Thank you for shopping with us 🙏
    </p>
    """

    msg = Message(
        "Order Invoice",
        sender=app.config['MAIL_USERNAME'],
        recipients=[user_email]
    )

    msg.html = body

    mail.send(msg)
# UPLOAD FOLDER     
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper
# HOME     
@app.route('/')
@login_required
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.close()

    return render_template('home.html', products=products, categories=categories)


# SEARCH     
@app.route('/search')
@login_required
def search():
    query = request.args.get('q')
    if not query:
        query = ""

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM products WHERE name LIKE %s", ("%" + query + "%",))
    products = cur.fetchall()

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.close()

    return render_template('home.html', products=products, categories=categories)


# ADMIN LOGIN     
@app.route('/admin/login', methods=['GET', 'POST'])
@login_required
def admin_login():
    error = ""

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
        admin = cur.fetchone()
        cur.close()

        if admin:
            session['admin'] = admin[0]
            return redirect('/admin')
        else:
            error = "Invalid Username or Password"

    return render_template('admin/login.html', error=error)


# ADMIN PANEL     
@app.route('/admin')
@login_required
def admin():
    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    # Products
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    # Categories
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    # 👤 Total Users
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    # 📦 Total Orders
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    # 💰 Total Revenue
    cur.execute("SELECT SUM(total_price) FROM orders")
    revenue = cur.fetchone()[0]
    revenue = revenue if revenue else 0

    cur.close()

    return render_template(
        'admin/admin.html',
        products=products,
        categories=categories,
        total_users=total_users,
        total_orders=total_orders,
        revenue=revenue
    )


# ADD PRODUCT     
@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.files['image']

        filename = ""

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cur.execute("INSERT INTO products(name, price, image) VALUES(%s,%s,%s)",
                    (name, price, filename))

        mysql.connection.commit()
        return redirect('/admin')

    cur.close()
    return render_template('admin/add.html')


# DELETE PRODUCT     
@app.route('/admin/delete/<int:id>')
def delete_product(id):
    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("SELECT image FROM products WHERE id=%s", (id,))
    product = cur.fetchone()

    if product and product[0]:
        path = os.path.join(app.config['UPLOAD_FOLDER'], product[0])
        if os.path.exists(path):
            os.remove(path)

    cur.execute("DELETE FROM products WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/admin')


# EDIT PRODUCT     
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cur.fetchone()

    if request.method == 'POST':

        name = request.form['name']
        price = request.form['price']
        image = request.files['image']

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            cur.execute("""UPDATE products SET name=%s, price=%s, image=%s WHERE id=%s""",
                        (name, price, filename, id))
        else:
            cur.execute("""UPDATE products SET name=%s, price=%s WHERE id=%s""",
                        (name, price, id))

        mysql.connection.commit()
        cur.close()

        return redirect('/admin')

    cur.close()
    return render_template("admin/edit.html", product=product)


# LOGIN / SIGNUP SYSTEM     
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
                    (name,email,password))
        mysql.connection.commit()
        cur.close()

        return redirect('/login')

    return render_template("signup.html")


@app.route('/login', methods=['GET','POST'])
def login():
    error = ""

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id,name FROM users WHERE email=%s AND password=%s",
                    (email,password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect('/')
        else:
            error = "Invalid Login"

    return render_template("login.html", error=error)

# ADD TO CART     
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):

    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM cart WHERE user_id=%s AND product_id=%s",
                (user_id, product_id))
    existing = cur.fetchone()

    if existing:
        cur.execute("""UPDATE cart SET quantity = quantity + 1
                       WHERE user_id=%s AND product_id=%s""",
                    (user_id, product_id))
    else:
        cur.execute("""INSERT INTO cart(user_id, product_id, quantity)
                       VALUES(%s,%s,%s)""",
                    (user_id, product_id, 1))

    mysql.connection.commit()
    cur.close()

    return redirect('/')


# CART     
@app.route('/cart')
@login_required
def cart():

    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT cart.id, products.name, products.price, cart.quantity, products.image
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    cart_items = cur.fetchall()
    cur.close()

    return render_template('cart.html', cart_items=cart_items)

@app.route('/cart/increase/<int:cart_id>')
def increase_qty(cart_id):

    cur = mysql.connection.cursor()
    cur.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=%s", (cart_id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/cart')

@app.route('/cart/decrease/<int:cart_id>')
def decrease_qty(cart_id):

    cur = mysql.connection.cursor()

    cur.execute("SELECT quantity FROM cart WHERE id=%s", (cart_id,))
    data = cur.fetchone()

    if data:
        qty = data[0]

        if qty <= 1:
            cur.execute("DELETE FROM cart WHERE id=%s", (cart_id,))
        else:
            cur.execute("""
                UPDATE cart 
                SET quantity = quantity - 1 
                WHERE id=%s
            """, (cart_id,))

    mysql.connection.commit()
    cur.close()

    return redirect('/cart')

@app.route('/cart/remove/<int:cart_id>')
def remove_item(cart_id):

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s", (cart_id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/cart')

# CHECKOUT     
@app.route('/checkout')
@login_required
def checkout():

    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT cart.id, products.name, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    cart_items = cur.fetchall()

    total = 0
    for item in cart_items:
        total += float(item[2]) * int(item[3])

    cur.close()

    return render_template('payment.html', cart_items=cart_items, total=total)


# PAYMENT SUCCESS (DEMO)     
@app.route('/payment_success')
@login_required
def payment_success():

    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    cur = mysql.connection.cursor()

    # 1. USER DETAILS (email + name)
    cur.execute("SELECT name, email FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    user_name = user[0]
    user_email = user[1]

    # 2. CART ITEMS FETCH
    cur.execute("""
        SELECT products.name, cart.quantity, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    cart_items = cur.fetchall()

    # 3. INSERT INTO ORDERS
    for item in cart_items:
        cur.execute("""
            INSERT INTO orders(user_id, product_id, quantity, total_price, status)
            VALUES(%s,%s,%s,%s,%s)
        """, (
            user_id,
            item[0],
            item[1],
            float(item[1]) * float(item[2]),
            "Paid"
        ))

    # 4. CLEAR CART
    cur.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))

    mysql.connection.commit()
    cur.close()

    # 5. SEND EMAIL (IMPORTANT NEW STEP)
    send_invoice_email(user_email, user_name, cart_items)
    flash("📩 Invoice email sent successfully!")
    return redirect('/invoice')
# INVOICE     
@app.route('/invoice')
@login_required
def invoice():

    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    cur = mysql.connection.cursor()

    cur.execute("SELECT name,email FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    cur.execute("""
        SELECT products.name, orders.quantity, orders.total_price
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE orders.user_id=%s
    """, (user_id,))

    items = cur.fetchall()

    grand_total = 0
    for item in items:
        grand_total += float(item[2])

    cur.close()

    return render_template('invoice.html', user=user, items=items, grand_total=grand_total)

@app.route('/admin/users')
def admin_users():

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, name, email
        FROM users
        ORDER BY id DESC
    """)

    users = cur.fetchall()
    cur.close()

    return render_template("admin/users.html", users=users)

# CONTACT     
@app.route('/contact', methods=['GET', 'POST'])
@login_required

def contact():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO contact_messages(name, email, message)
            VALUES(%s,%s,%s)
        """, (name, email, message))

        mysql.connection.commit()
        cur.close()

        return "Message Sent Successfully!"

    return render_template("contact.html")

@app.route('/admin/contacts')
def admin_contacts():

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, name, email, message
        FROM contact_messages
        ORDER BY id DESC
    """)

    messages = cur.fetchall()
    cur.close()

    return render_template("admin/contacts.html", messages=messages)

# ADMIN CATEGORIES     
@app.route('/admin/categories')
def admin_categories():

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.close()

    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
def add_category():

    if 'admin' not in session:
        return redirect('/admin/login')

    name = request.form['name']

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO categories(name) VALUES(%s)", (name,))
    mysql.connection.commit()
    cur.close()

    return redirect('/admin/categories')

@app.route('/admin/categories/delete/<int:id>')
def delete_category(id):

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM categories WHERE id=%s", (id,))

    mysql.connection.commit()
    cur.close()

    return redirect('/admin/categories')

# ORDERS     
@app.route('/orders')
@login_required
def orders():

    user_id = session.get('user_id')   

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT orders.id,
               products.name,
               orders.quantity,
               orders.total_price,
               orders.status
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE orders.user_id=%s
        ORDER BY orders.id DESC
    """, (user_id,))

    orders = cur.fetchall()
    cur.close()

    return render_template("orders.html", orders=orders)

@app.route('/add_to_wishlist/<int:product_id>')
@login_required
def add_to_wishlist(product_id):

    user_id = session.get('user_id')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT * FROM wishlist
        WHERE user_id=%s AND product_id=%s
    """, (user_id, product_id))

    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO wishlist(user_id, product_id)
            VALUES(%s,%s)
        """, (user_id, product_id))

        mysql.connection.commit()

    cur.close()

    return redirect(request.referrer or '/')

@app.route('/wishlist')
@login_required
def wishlist():

    user_id = session.get('user_id')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT wishlist.id,
               products.name,
               products.price,
               products.image
        FROM wishlist
        JOIN products
        ON wishlist.product_id = products.id
        WHERE wishlist.user_id=%s
    """, (user_id,))

    wishlist_items = cur.fetchall()

    cur.close()

    return render_template(
        'wishlist.html',
        wishlist_items=wishlist_items
    )
    
@app.route('/wishlist/remove/<int:id>')
@login_required
def remove_wishlist(id):

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM wishlist WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()
    cur.close()

    return redirect('/wishlist')

@app.route('/admin/cart')
def admin_cart():

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT cart.id,
               products.name,
               products.price,
               cart.quantity,
               products.image
        FROM cart
        JOIN products ON cart.product_id = products.id
    """)

    cart_items = cur.fetchall()
    cur.close()

    return render_template('admin/cart.html', cart_items=cart_items)

@app.route('/logout')
def logout():
    session.clear()
    response = redirect('/login')
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route('/admin/logout')
def admin_logout():

    session.pop('admin', None)
    return redirect('/admin/login')

@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route('/test-mail')
def test_mail():

    msg = Message(
        "Test Email",
        sender=app.config['MAIL_USERNAME'],
        recipients=["receiver@gmail.com"],
        body="Flask SMTP working fine!"
    )

    mail.send(msg)

    return "Email Sent Successfully!"

@app.route('/category/<int:category_id>')
def category_page(category_id):

    cur = mysql.connection.cursor()

    # category name (optional)
    cur.execute("SELECT * FROM categories WHERE id=%s", (category_id,))
    category = cur.fetchone()

    # subcategories of this category
    cur.execute("""
        SELECT id, name
        FROM subcategories
        WHERE category_id=%s
    """, (category_id,))
    subcategories = cur.fetchall()

    cur.close()

    return render_template(
        "subcategory_page.html",
        category=category,
        subcategories=subcategories
    )
    
@app.route('/subcategory/<int:sub_id>')
def subcategory_products(sub_id):

    cur = mysql.connection.cursor()

    # subcategory name + category id (optional)
    cur.execute("SELECT * FROM subcategories WHERE id=%s", (sub_id,))
    subcategory = cur.fetchone()

    # products under this subcategory
    cur.execute("""
        SELECT id, name, price, image
        FROM products
        WHERE subcategory_id=%s
    """, (sub_id,))

    products = cur.fetchall()
    cur.close()

    return render_template(
        "products_page.html",
        subcategory=subcategory,
        products=products
    )
    
@app.route('/admin/subcategories/add', methods=['POST'])
def add_subcategory():

    if 'admin' not in session:
        return redirect('/admin/login')

    name = request.form['name']
    category_id = request.form['category_id']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO subcategories(name, category_id)
        VALUES(%s,%s)
    """, (name, category_id))

    mysql.connection.commit()
    cur.close()

    return redirect('/admin/categories')

@app.route('/admin/subcategories')
def admin_subcategories():

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    cur.execute("""
        SELECT subcategories.id, subcategories.name, categories.name
        FROM subcategories
        JOIN categories ON subcategories.category_id = categories.id
    """)
    subcategories = cur.fetchall()

    cur.close()

    return render_template(
        "admin/subcategories.html",
        categories=categories,
        subcategories=subcategories
    )

@app.route('/admin/subcategories/delete/<int:id>')
def delete_subcategory(id):

    if 'admin' not in session:
        return redirect('/admin/login')

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM subcategories WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/admin/subcategories')

# RUN     
if __name__ == '__main__':
    app.run(debug=True)