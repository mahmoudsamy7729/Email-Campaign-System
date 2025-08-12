# 📧 Email Campaign System

A Django-based application for managing and sending bulk or targeted email campaigns with HTML templates, SMTP integration, and user authentication.

---

## 🚀 Features

- 🔐 **User Authentication** – Sign up, log in, log out, email verification
- 📩 **Email Sending** – Send emails via SMTP (Gmail, custom domain, etc.)
- 🎨 **HTML Email Templates** – Design and send styled emails
- 📊 **Campaign Management** – Create, edit, and track campaigns
- ⚙️ **Environment Configuration** – Easily configurable via `.env` file
- 🛡️ **Secure Settings** – Sensitive keys are kept out of the repository

---

## 📂 Project Structure

```
Email-Campaign-System/
│
├── accounts/           # Custom user model and authentication logic
├── core/               # Core settings and utilities
├── templates/          # HTML templates (emails, pages, etc.)
├── manage.py           # Django management script
├── .env.example        # Example environment variables file
└── requirements.txt    # Project dependencies
```

---

## 🛠 Installation

1️⃣ **Clone the Repository**
```bash
git clone https://github.com/your-username/email-campaign-system.git
cd email-campaign-system
```

2️⃣ **Create and Activate a Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate    # On macOS/Linux
venv\Scripts\activate       # On Windows
```

3️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
```

4️⃣ **Set Up Environment Variables**
Copy the example file and edit values:
```bash
cp .env.example .env
```
Edit `.env` and add your **SECRET_KEY**, **email credentials**, and other configs.

5️⃣ **Run Migrations**
```bash
python manage.py migrate
```

6️⃣ **Create a Superuser**
```bash
python manage.py createsuperuser
```

7️⃣ **Start the Development Server**
```bash
python manage.py runserver
```
Now visit: [http://localhost:8000](http://localhost:8000)

---

## ⚙️ Environment Variables

Your `.env` file should include:

```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
AUTH_USER_MODEL=accounts.User
```

---

## 📧 Email Sending Setup

1. Use **Gmail** or your domain’s SMTP server  
2. For Gmail, enable **App Passwords** and use that in `.env`  
3. Test sending:
```bash
python manage.py shell
from django.core.mail import send_mail
send_mail('Test Subject', 'Hello from Email Campaign System', 'your-email@example.com', ['recipient@example.com'])
```

---

## 📜 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

1. Fork the project  
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)  
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)  
4. Push to the branch (`git push origin feature/AmazingFeature`)  
5. Open a Pull Request

---

## 📌 Notes

- Do **NOT** commit your `.env` file to GitHub  
- Always use `.env.example` for sharing configs  
- For production, set `DEBUG=False` and secure cookies

---
