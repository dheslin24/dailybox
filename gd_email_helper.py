import smtplib

# from email.MIMEMultipart import MIMEMultipart
from email.mime.multipart import MIMEMultipart
# from email.MIMEText import MIMEText
from email.mime.text import MIMEText

def send_gd_email():
    try:
        msg = MIMEMultipart()
        msg.set_unixfrom('byg_admin')
        msg['From'] = 'todd@byggaming.com'
        msg['To'] = 'dheslin@yahoo.com'
        msg['Subject'] = 'hello, mr. thompson'
        message = "I think he's talking to you!"
        msg.attach(MIMEText(message))

        mailserver = smtplib.SMTP_SSL('smtpout.secureserver.net', 465)
        mailserver.ehlo()
        mailserver.login('dheslin@yahoo.com', 'h0mers!mpson')

        mailserver.sendmail('todd@byggaming.com','dheslin@yahoo.com',msg.as_string())

        mailserver.quit()

    except Exception as e:
        print(f"ERROR!  {e}")
send_gd_email()