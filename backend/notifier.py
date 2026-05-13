import smtplib
from email.message import EmailMessage

def send_email_alert(subject, body, to_email):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "support@company.com"
    msg["To"] = to_email
    msg.set_content(body)

    # Example using Gmail SMTP (use app password)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("your_email@gmail.com", "APP_PASSWORD")
        smtp.send_message(msg)
