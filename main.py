import smtplib
import os

from flask import Flask, render_template, request
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)


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
# @app.route('/property')
# def about():
#     return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
