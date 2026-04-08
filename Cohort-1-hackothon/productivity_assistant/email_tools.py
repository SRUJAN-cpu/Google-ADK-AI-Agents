"""
Email tools for the productivity assistant.
Sends meeting invite emails with Google Meet link + Add to Calendar link.

Setup:
  1. Enable 2-Step Verification on your Gmail account
  2. Go to myaccount.google.com → Security → App passwords
  3. Generate one for "Mail" and add to .env:
     GMAIL_SENDER=forprojects436@gmail.com
     GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
"""

import os
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText

_SENDER = os.getenv('GMAIL_SENDER', '')
_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')


def send_meeting_invite(
    to_email: str,
    meeting_title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = '',
    location: str = '',
    organizer_name: str = 'Productivity Assistant',
) -> dict:
    """
    Send a meeting invite email with a Google Meet link and Add to Calendar link.

    Args:
        to_email: Recipient email address.
        meeting_title: Title of the meeting.
        date: Date in YYYY-MM-DD format, e.g. '2026-04-09'.
        start_time: Start time in HH:MM (24h), e.g. '15:00'.
        end_time: End time in HH:MM (24h), e.g. '16:00'.
        description: Optional agenda or notes.
        location: Optional location or existing meeting link.
        organizer_name: Name shown in the email sign-off.

    Returns:
        dict with status and message.
    """
    if not _SENDER or not _APP_PASSWORD:
        return {
            'status': 'error',
            'message': 'GMAIL_SENDER or GMAIL_APP_PASSWORD not set in .env.',
        }

    try:
        cal_link = _build_gcal_link(meeting_title, date, start_time, end_time, description, location)
        meet_link = location if location.startswith('http') else 'https://meet.google.com/new'

        try:
            dt = datetime.strptime(date, '%Y-%m-%d')
            display_date = dt.strftime('%A, %B %d, %Y')
        except Exception:
            display_date = date

        body = f"""You're invited to a meeting!

Meeting  : {meeting_title}
Date     : {display_date}
Time     : {start_time} – {end_time}
Location : {location or 'Google Meet'}
{f'Agenda   : {description}' if description else ''}

Join Google Meet : {meet_link}
Add to Calendar  : {cal_link}

—
Sent by {organizer_name}
"""

        msg = MIMEText(body)
        msg['Subject'] = f"Meeting Invite: {meeting_title}"
        msg['From'] = _SENDER
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(_SENDER, _APP_PASSWORD)
            server.sendmail(_SENDER, to_email, msg.as_string())

        return {
            'status': 'success',
            'message': f"Invite for '{meeting_title}' sent to {to_email}.",
            'meet_link': meet_link,
            'cal_link': cal_link,
        }

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _build_gcal_link(title, date, start_time, end_time, description, location):
    date_compact = date.replace('-', '')
    start_compact = start_time.replace(':', '') + '00'
    end_compact = end_time.replace(':', '') + '00'
    dates = f"{date_compact}T{start_compact}/{date_compact}T{end_compact}"
    params = {
        'action': 'TEMPLATE',
        'text': title,
        'dates': dates,
        'details': description,
        'location': location or 'Google Meet',
    }
    return 'https://calendar.google.com/calendar/r/eventedit?' + urllib.parse.urlencode(params)
