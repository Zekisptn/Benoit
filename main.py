import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
from dotenv import load_dotenv
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import base64
import sqlite3
import mysql.connector


load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'benoit'

mysql = MySQL(app)

# EMAIL_PENGIRIM = os.getenv("EMAIL_PENGIRIM")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# EMAIL_PENERIMA = os.getenv("EMAIL_PENERIMA")
# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Custom filter to encode image data to base64
@app.template_filter('b64encode')
def b64encode_filter(data):
    return base64.b64encode(data).decode('utf-8')

# Register the filter
app.jinja_env.filters['b64encode'] = b64encode_filter

@app.route('/')
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Fetch properties with status 'masih tersedia'
    cursor.execute('SELECT * FROM properti WHERE status_properti = %s', ('masih tersedia',))
    available_properties = cursor.fetchall()
    return render_template('index.html', properties=available_properties)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/kirim', methods=['POST'])
def kirim_pesan():
    nama = request.form['name']
    nomor = request.form['number']
    pesan = request.form['message']

    # Save the form data to the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('INSERT INTO formulir (nama_pengirim, nomor_pengirim, isi_pesan) VALUES (%s, %s, %s)', (nama, nomor, pesan))
    mysql.connection.commit()

    return {'status': 'success', 'message': 'Pesan berhasil disimpan. Terima kasih!'}

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    registration_success = session.pop('registration_success', None)
    attempts = session.get('attempts', 0)  # ambil attempts dari session (default 0)

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM login WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id_user']
            session['username'] = account['username']
            session.pop('attempts', None)  # reset attempts setelah berhasil login
            return redirect(url_for('dashboard'))
        else:
            attempts += 1
            session['attempts'] = attempts
            if attempts >= 5:
                session.pop('attempts', None)  # reset attempts supaya tidak stuck
                session['reset_email_username'] = request.form['username']  # simpan username yg mau reset
                return redirect(url_for('reset_password_email'))
            msg = f'Incorrect username/password! Attempts: {attempts}/5'

    return render_template('login.html', msg=msg, registration_success=registration_success)


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_email():
    msg = ''
    if request.method == 'POST' and 'email' in request.form:
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM login WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            session['reset_user_id'] = account['id_user']
            return redirect(url_for('set_new_password'))
        else:
            msg = 'Email tidak ditemukan!'

    return render_template('reset_pass.html', msg=msg)

@app.route('/set-new-password', methods=['GET', 'POST'])
def set_new_password():
    msg = ''
    if 'reset_user_id' not in session:
        return redirect(url_for('login'))  # kalau belum reset, langsung login

    if request.method == 'POST' and 'password' in request.form:
        password = request.form['password']
        user_id = session['reset_user_id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE login SET password = %s WHERE id_user = %s', (password, user_id,))
        mysql.connection.commit()
        session.pop('reset_user_id', None)
        msg = 'Password berhasil diubah. Silakan login kembali.'
        return redirect(url_for('login'))

    return render_template('new_pass.html', msg=msg)


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'nama_user' in request.form:
        nama_user = request.form['nama_user']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM login WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email or not nama_user:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO login (nama_user, username, password, email) VALUES (%s, %s, %s, %s)', (nama_user, username, password, email,))
            mysql.connection.commit()
            session['registration_success'] = 'You have successfully registered! Please log in.'
            return redirect(url_for('login'))
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        # Use flask_mysqldb's connection
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Count properties grouped by status_properti
        cursor.execute('SELECT status_properti, COUNT(*) as property_count FROM properti GROUP BY status_properti')
        properties = cursor.fetchall()

        # Initialize property_data with default values
        property_data = {
            'labels': [],
            'values': []
        }

        # Populate property_data with the results
        if properties:
            property_data['labels'] = [prop['status_properti'] for prop in properties]
            property_data['values'] = [prop['property_count'] for prop in properties]

        return render_template('dashboard.html', username=session['username'], property_data=property_data)
    return redirect(url_for('login'))


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/properties')
def list_properties():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM properti')
    properties = cursor.fetchall()
    return render_template('properties.html', properties=properties)

@app.route('/add-property', methods=['GET', 'POST'])
def add_property():
    if request.method == 'POST':
        # Handle form data
        nama_properti = request.form['nama_properti']
        gambar_rumah = request.files['gambar_rumah'].read()
        luas_rumah = request.form['luas_rumah']
        kamar_mandi = request.form['kamar_mandi']
        kasur = request.form['kasur']
        status_properti = request.form['status_properti']
        
        # Insert data into the database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO properti (nama_properti, gambar_rumah, luas_rumah, kamar_mandi, kasur, status_properti) VALUES (%s, %s, %s, %s, %s, %s)', 
                    (nama_properti, gambar_rumah, luas_rumah, kamar_mandi, kasur, status_properti))
        mysql.connection.commit()

        # Flash message to notify success
        flash('Property berhasil ditambahkan!', 'success')

        # return redirect(url_for('dashboard'))

    return render_template('add_property.html')


@app.route('/edit-property/<int:id>', methods=['GET', 'POST'])
def edit_property(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM properti WHERE id_properti = %s', (id,))
    property = cursor.fetchone()
    
    if request.method == 'POST':
        nama_properti = request.form['nama_properti']
        # Check if a new image is uploaded
        if 'gambar_rumah' in request.files and request.files['gambar_rumah'].filename != '':
            gambar_rumah = request.files['gambar_rumah'].read()
        else:
            gambar_rumah = property['gambar_rumah']  # Retain existing image
        luas_rumah = request.form['luas_rumah']
        kamar_mandi = request.form['kamar_mandi']
        kasur = request.form['kasur']
        status_properti = request.form['status_properti']

        cursor.execute('UPDATE properti SET nama_properti = %s, gambar_rumah = %s, luas_rumah = %s, kamar_mandi = %s, kasur = %s, status_properti = %s WHERE id_properti = %s', 
                    (nama_properti, gambar_rumah, luas_rumah, kamar_mandi, kasur, status_properti, id))
        mysql.connection.commit()
        
        flash('Property berhasil diperbarui!', 'success')
        return redirect(url_for('list_properties'))

    return render_template('edit_property.html', property=property)

@app.route('/delete-property/<int:id>', methods=['POST'])
def delete_property(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM properti WHERE id_properti = %s', (id,))
    mysql.connection.commit()
    return redirect(url_for('list_properties'))

@app.route('/logout')
def logout():
    session.clear()  # atau session.pop('loggedin', None) kalau mau spesifik
    return redirect(url_for('login'))

@app.route('/form-logs')
def form_logs():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM formulir ORDER BY date DESC')
    form_entries = cursor.fetchall()
    return render_template('form_logs.html', form_entries=form_entries)

@app.route('/admin-redirect')
def admin_redirect():
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
