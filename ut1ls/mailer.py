import os
from dotenv import load_dotenv
load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource

from datetime import datetime as dt
from datetime import timedelta
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from mimetypes import guess_type as guess_mime_type

# gmail v1
# calendar v3

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://mail.google.com/', 'https://www.googleapis.com/auth/calendar.readonly']
EMAIL = os.getenv('EMAIL_USER')

class GoogleAPI:
    def authenticate(self, service, version) -> Resource:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('files/google-api.json'):
            creds = Credentials.from_authorized_user_file('files/google-api.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'files/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('files/google-api.json', 'w') as token:
                token.write(creds.to_json())

        try:
            r = build(serviceName=service, version=version, credentials=creds)
        except HttpError as error:
            print('An error occurred: %s' % error)
        else:
            return r


class Mailer(GoogleAPI):
    """"Implémentation des fonctions nécessaires à l'envoi de mail."""
    def __init__(self) -> None:
        self.service = self.authenticate('gmail', 'v1')

    def add_attachment(self, message: MIMEMultipart, filename: str):
        if os.path.exists(filename):
            content_type, encoding = guess_mime_type(filename)
            if content_type is None:  # and encoding is not None:
                content_type = 'application/octet-stream'
            main_type, sub_type = content_type.split('/', 1)
            if main_type == 'text':
                fp = open(filename, 'rb')
                msg = MIMEText(fp.read().decode(), _subtype=sub_type)
                fp.close()
            elif main_type == 'image':
                fp = open(filename, 'rb')
                msg = MIMEImage(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == 'audio':
                fp = open(filename, 'rb')
                msg = MIMEAudio(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == 'application':
                fp = open(filename, 'rb')
                msg = MIMEApplication(fp.read(), _subtype=sub_type)
                fp.close()
            else:
                fp = open(filename, 'rb')
                msg = MIMEBase(main_type, sub_type)
                msg.set_payload(fp.read())
                fp.close()
            filename = os.path.basename(filename)
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            message.attach(msg)

    def build_message(self, destination, obj, body, attachments=[]):
        if not attachments:  # no attachments given
            message = MIMEText(body)
            message['to'] = destination
            message['from'] = self.mail
            message['subject'] = obj
        else:
            message = MIMEMultipart()
            message['to'] = destination
            message['from'] = self.mail
            message['subject'] = obj
            message.attach(MIMEText(body))
            for filename in attachments:
                self.add_attachment(message, filename)
        return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}

    def send_message(self, destination: str, obj: str, body: str, attachments=[]):
        return self.service.users().messages().send(
            userId="me",
            body=self.build_message(destination, obj, body, attachments)
        ).execute()

class Agenda(GoogleAPI):
    def __init__(self):
        self.service = self.authenticate('calendar', 'v3')

    def events(self, _from : dt = dt.utcnow(), to = (dt.utcnow() + timedelta(days=7)), limit=10):
        # Call the Calendar API
        _from = _from.isoformat() + 'Z'  # 'Z' indicates UTC time
        to = to.isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=os.getenv('CALENDAR_ID', 'primary'), timeMin=_from, timeMax=to,
                                            maxResults=limit, singleEvents=True,
                                            orderBy='startTime').execute()
        
        return events_result.get('items', [])
    
    def events_of(self, date : dt = dt.utcnow(), to : int = 1):
        date = date.isoformat() + 'Z'
        tomorrow = (dt.utcnow() + timedelta(days=to)).isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=os.getenv('CALENDAR_ID', 'primary'), timeMin=date, timeMax=tomorrow).execute()

        return events_result.get('items', [])