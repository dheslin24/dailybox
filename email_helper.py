import os
import requests
import logging

RESEND_API_KEY = os.getenv('RESEND_API_KEY')
DEFAULT_FROM   = 'BYGaming <noreply@byggaming.com>'
DOMAIN         = 'byggaming.com'


def send_email(rcpt, subject, body_html, body_text='', from_username=None):
    if not RESEND_API_KEY:
        logging.error("RESEND_API_KEY not set — email not sent")
        return False
    if from_username:
        sender = f'BYGaming <{from_username}@{DOMAIN}>'
    else:
        sender = DEFAULT_FROM
    resp = requests.post(
        'https://api.resend.com/emails',
        headers={'Authorization': f'Bearer {RESEND_API_KEY}', 'Content-Type': 'application/json'},
        json={
            'from':    sender,
            'to':      rcpt if isinstance(rcpt, list) else [rcpt],
            'subject': subject,
            'html':    body_html,
            'text':    body_text or subject,
        },
    )
    if not resp.ok:
        logging.error("Resend error %s: %s", resp.status_code, resp.text)
    return resp.ok
