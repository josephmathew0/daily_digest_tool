import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(BASE_DIR / ".env")

    credentials_path = BASE_DIR / os.getenv("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")
    token_path = BASE_DIR / os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")

    if not credentials_path.exists():
        raise FileNotFoundError(f"Missing Gmail credentials file: {credentials_path}")

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    credentials = flow.run_local_server(port=0)
    token_path.write_text(credentials.to_json())
    print(f"Saved Gmail token to {token_path}")


if __name__ == "__main__":
    main()
