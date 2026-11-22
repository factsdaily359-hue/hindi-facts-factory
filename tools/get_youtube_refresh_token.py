from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
    )
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
    )
    if not credentials.refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Re-run and approve access "
            "using the correct Google account."
        )
    print("\nAUTHORIZATION SUCCESSFUL")
    print("Copy the value below into the GitHub Actions secret YOUTUBE_REFRESH_TOKEN.")
    print("\nYOUTUBE_REFRESH_TOKEN=" + credentials.refresh_token)
    print("\nDo not share this token or commit it to GitHub.")

if __name__ == "__main__":
    main()
