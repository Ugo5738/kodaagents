from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow


def get_google_credentials():
    # # Use this if you have a client_secret.json file
    # flow = Flow.from_client_secrets_file(
    #     'path/to/your/client_secret.json',
    #     scopes=['https://www.googleapis.com/auth/gmail.send'],
    #     redirect_uri='urn:ietf:wg:oauth:2.0:oob')

    # If you don't have the file, use this instead:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                # "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=['https://www.googleapis.com/auth/gmail.send']
    )
    flow.redirect_uri = settings.GMAIL_REDIRECT_URI

    authorization_url, _ = flow.authorization_url(prompt='consent')

    print(f"Please visit this URL to authorize the application: {authorization_url}")
    code = input("Enter the authorization code: ")

    flow.fetch_token(code=code)

    credentials = flow.credentials

    print(f"Access token: {credentials.token}")
    print(f"Refresh token: {credentials.refresh_token}")
