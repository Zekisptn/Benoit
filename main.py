import smtplib
import os
from flask import Flask, render_template, request, redirect, url_for, session
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
from dotenv import load_dotenv
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'benoit'

mysql = MySQL(app)

EMAIL_PENGIRIM = os.getenv("EMAIL_PENGIRIM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_PENERIMA = os.getenv("EMAIL_PENERIMA")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/kirim', methods=['POST'])
def kirim_pesan():
    nama = request.form['name']
    email_user = request.form['email']
    subjek = request.form['subject']
    pesan = request.form['message']

    isi_email = f"Nama: {nama}\nEmail: {email_user}\nSubjek: {subjek}\n\nPesan:\n{pesan}"
    msg = MIMEText(isi_email, _charset='utf-8')
    msg['Subject'] = Header(f"Pesan dari {nama} - {subjek}", 'utf-8')
    msg['From'] = formataddr((str(Header(nama, 'utf-8')), EMAIL_PENGIRIM))
    msg['To'] = EMAIL_PENERIMA
    msg['Reply-To'] = email_user

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_PENGIRIM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_PENGIRIM, EMAIL_PENERIMA, msg.as_string())
        server.quit()
        return "<h3>Pesan berhasil dikirim. Terima kasih!</h3>"
    except Exception as e:
        return f"<h3>Gagal mengirim email: {e}</h3>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    registration_success = session.pop('registration_success', None)  # ambil pesan sukses register (sekali saja)
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
            return redirect(url_for('dashboard'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('login.html', msg=msg, registration_success=registration_success)

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
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
