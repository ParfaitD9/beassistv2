import datetime
import os
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource

from datetime import datetime as dt
from datetime import timedelta

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
EMAIL = os.getenv('EMAIL_USER')

class Agenda:
    def __init__(self, mail):
        self.mail = mail
        self.scopes = SCOPES
        self.service = self.authenticate()
    
    def authenticate(self) -> Resource:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('files/agenda.json'):
            creds = Credentials.from_authorized_user_file('files/agenda.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'files/credentials.json', self.scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('files/agenda.json', 'w') as token:
                token.write(creds.to_json())

        try:
            service = build('calendar', 'v3', credentials=creds)
        except HttpError as error:
            print('An error occurred: %s' % error)
        else:
            return service
    
    def events(self, calendarId='primary', _from : dt = dt.utcnow(), to = (dt.utcnow() + timedelta(days=7)), limit=10):
        # Call the Calendar API
        _from = _from.isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = self.service.events().list(calendarId=calendarId, timeMin=_from,
                                            maxResults=limit, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])

        return [{'event' : event['summary'], 'date':event['start'].get('dateTime', event['start'].get('date'))} for event in events]

if __name__ == '__main__':
    a = Agenda(EMAIL)
    a.events()