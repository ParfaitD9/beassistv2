import os
import io
import hashlib as hb
from datetime import datetime as dt
from datetime import timedelta
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication

from dotenv import load_dotenv

load_dotenv()

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.discovery import build

from mimetypes import guess_type as guess_mime_type


# gmail v1
# calendar v3

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar.readonly",
]
EMAIL = os.getenv("EMAIL_USER")


class GoogleAPI:
    def authenticate(self, service, version, scopes) -> Resource:
        """Authentication function from service account for google API"""
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("files/google-api.json"):
            creds = credentials.Credentials.from_authorized_user_file(
                "files/google-api.json", scopes
            )
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "files/google-api.json", scopes
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("files/token.json", "w") as token:
                token.write(creds.to_json())

        return build(serviceName=service, version=version, credentials=creds)


class Mailer(GoogleAPI):
    """ "Implémentation des fonctions nécessaires à l'envoi de mail."""

    SCOPES = [
        "https://mail.google.com/",
    ]

    def __init__(self) -> None:
        self.service = self.authenticate("gmail", "v1", Mailer.SCOPES)
        self.mail = EMAIL

    def add_attachment(self, message: MIMEMultipart, filename: str):
        if os.path.exists(filename):
            content_type, _ = guess_mime_type(filename)
            if content_type is None:  # and encoding is not None:
                content_type = "application/octet-stream"
            main_type, sub_type = content_type.split("/", 1)
            if main_type == "text":
                fp = open(filename, "rb")
                msg = MIMEText(fp.read().decode(), _subtype=sub_type)
                fp.close()
            elif main_type == "image":
                fp = open(filename, "rb")
                msg = MIMEImage(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == "audio":
                fp = open(filename, "rb")
                msg = MIMEAudio(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == "application":
                fp = open(filename, "rb")
                msg = MIMEApplication(fp.read(), _subtype=sub_type)
                fp.close()
            else:
                fp = open(filename, "rb")
                msg = MIMEBase(main_type, sub_type)
                msg.set_payload(fp.read())
                fp.close()
            filename = os.path.basename(filename)
            msg.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(msg)

    def build_message(self, destination, obj, body, attachments=[]):
        if not attachments:  # no attachments given
            message = MIMEText(body)
            message["to"] = destination
            message["from"] = self.mail
            message["subject"] = obj
        else:
            message = MIMEMultipart()
            message["to"] = destination
            message["from"] = self.mail
            message["subject"] = obj
            message.attach(MIMEText(body))
            for filename in attachments:
                self.add_attachment(message, filename)
        return {"raw": urlsafe_b64encode(message.as_bytes()).decode()}

    def send_message(self, destination: str, obj: str, body: str, attachments=[]):
        return (
            self.service.users()
            .messages()
            .send(
                userId="me",
                body=self.build_message(destination, obj, body, attachments),
            )
            .execute()
        )


class Agenda(GoogleAPI):
    """Google agenda implementation"""

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self):
        self.service = self.authenticate("calendar", "v3", Agenda.SCOPES)
        self.mail = EMAIL

    def events(
        self, _from: dt = dt.utcnow(), to=(dt.utcnow() + timedelta(days=7)), limit=10
    ):
        # Call the Calendar API
        _from = _from.isoformat() + "Z"  # 'Z' indicates UTC time
        to = to.isoformat() + "Z"
        events_result = (
            self.service.events()
            .list(
                calendarId=os.getenv("CALENDAR_ID", "primary"),
                timeMin=_from,
                timeMax=to,
                maxResults=limit,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])

    def events_of(self, date: dt = dt.utcnow(), to: int = 1):
        date = date.isoformat() + "Z"
        tomorrow = (dt.utcnow() + timedelta(days=to)).isoformat() + "Z"
        events_result = (
            self.service.events()
            .list(
                calendarId=os.getenv("CALENDAR_ID", "primary"),
                timeMin=date,
                timeMax=tomorrow,
            )
            .execute()
        )
        return events_result.get("items", [])


class Drive(GoogleAPI):
    """Google drive implementation"""

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self) -> None:
        self.service: Resource = self.authenticate("drive", "v3", Drive.SCOPES)

    @staticmethod
    def hash_of(path):
        """Generate SHA256 hash of file"""
        with open(path, "rb") as f:
            hasher = hb.md5()
            while True:
                data = f.read(256 * 1024)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()

    def create_folder(self, name: str) -> str | None:
        """Create a folder and prints the folder ID
        Args:
            name: folder's name on Drive
        Returns : Folder Id
        """
        try:
            metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
            # pylint: disable=no-member
            file = self.service.files().create(body=metadata, fields="id").execute()
        except HttpError as error:
            print(f"An error occurred: {error}")
        else:
            print(f"Dossier créé avec l'ID : {file.get('id')}.")
            return file.get("id")

    def upload(self, path, filename=None, upload_dir=None, _hash=None) -> dict | None:
        """Upload file to Google Drive
        Args :
            path : file to upload path
            filename : name of file (optional)
            upload_dir : Directory to upload file on Drive (optional)
            _hash : SHA 256 hash of file (optional)
        Return : file ID on Drive
        """
        if os.path.exists(path):
            content_type, _ = guess_mime_type(path)
            if content_type is None:
                content_type = "application/octet-stream"

            if not filename:
                filename = os.path.basename(path)

            metadata = {
                "name": filename,
            }
            if _hash:
                metadata.update(
                    {
                        "appProperties": {
                            "hash": _hash,
                        }
                    }
                )

            if upload_dir:
                metadata.update(
                    {
                        "parents": [
                            upload_dir,
                        ]
                    }
                )

            media = MediaFileUpload(path, mimetype=content_type)

            try:
                file = (
                    self.service.files()
                    .create(body=metadata, media_body=media, fields="*")
                    .execute()
                )
            except (HttpError,) as e:  # pylint: disable=invalid-name
                print(f"HttpError : {e}")
                print("Le fichier n'a pas pu être uploadé")
            else:
                print(f"Fichier updloadé avec l'ID : {file.get('id')}")
                return file

    def get(self, _id) -> dict[str, str]:
        """Fetch specific file from Google Drive"""
        try:
            # pylint: disable=no-member
            response = self.service.files().get(fileId=_id, fields="*").execute()
        except (HttpError,) as e:  # pylint: disable=invalid-name
            print(e)
        else:
            return response

    def get_by(self, _hash):
        """Fetch file through properties"""
        response = (
            self.service.files()
            .list(  # pylint: disable= no-member
                fields="*", q=f"appProperties has {{ key='hash' and value='{_hash}' }}"
            )
            .execute()
        )
        response = response.get("files", [])
        return response[0] if response else None

    def downlaod(self, _id):
        """Downloads a file
        Args:
            _id: ID of the file to download
        Returns : IO object with location.
        """
        try:
            # pylint: disable=no-member
            request = self.service.files().get_media(
                fileId=_id,
            )
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}.")
        except HttpError as error:
            print(f"An error occurred: {error}")
        else:
            return file.getvalue()

    def delete(self, _id):
        """Delete file from Drive"""
        try:
            self.service.files().delete(
                fileId=_id
            ).execute()  # pylint: disable=no-member
        except (HttpError,) as e:  # pylint: disable=invalid-name
            print(f"{e.__class__} : {e.args[0]}")
        else:
            print(f"Fichier {_id} supprimé avec succès!")

    def ls(self, opts="*"):  # pylint: disable=invalid-name
        """List Drive files"""
        try:
            #
            # pylint: disable=no-member
            if opts == "dirs":
                response = (
                    self.service.files()
                    .list(
                        fields="nextPageToken, " "files(id, name, size), kind",
                        q="mimeType = 'application/vnd.google-apps.folder'",
                    )
                    .execute()
                )
            elif opts == "files":
                response = (
                    self.service.files()
                    .list(
                        fields="nextPageToken, " "files(id, name, size), kind",
                        q="mimeType != 'application/vnd.google-apps.folder'",
                    )
                    .execute()
                )
            elif opts == "*":
                response = (
                    self.service.files()
                    .list(
                        fields="nextPageToken, " "files(id, name, size), kind",
                    )
                    .execute()
                )
            else:
                response = (
                    self.service.files()
                    .list(
                        fields="nextPageToken, " "files(id, name, size), kind",
                        q=f"mimeType = '{opts}'",
                    )
                    .execute()
                )
        except (HttpError,) as e:  # pylint: disable=invalid-name
            print(e)
        else:
            return response.get("files", [])

    @staticmethod
    def format_clause(**kwargs):
        return (
            " and ".join([f"{key} = '{val}'" for key, val in kwargs.items()])
            if kwargs
            else None
        )

    def close(self):
        """Close connection"""
        self.service.close()
