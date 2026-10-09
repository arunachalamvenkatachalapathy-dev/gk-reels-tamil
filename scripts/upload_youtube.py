"""Channel-guarded YouTube Shorts uploader. No comment or other side effects."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_youtube_client():
    """Build an API client only after verifying the exact authorized channel."""
    expected = os.environ.get("YT_CHANNEL_ID", "").strip()
    if expected != "UC5ZLfNHUI4z92IW69KVTGxg":
        raise RuntimeError("YT_CHANNEL_ID must match the verified Tamil channel.")
    client_id = os.environ["YT_CLIENT_ID"].strip()
    client_secret = os.environ["YT_CLIENT_SECRET"].strip()
    refresh_token = os.environ["YT_REFRESH_TOKEN"].strip()
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri=TOKEN_URI,
    )
    youtube = build("youtube", "v3", credentials=credentials)
    channels = youtube.channels().list(part="id", mine=True).execute().get("items", [])
    actual = [channel.get("id") for channel in channels]
    if actual != [expected]:
        raise RuntimeError("OAuth identity mismatch: refusing to upload to a non-Tamil channel.")
    return youtube


def upload_short(video_path, title, description, tags=None):
    """Upload one MP4 as a public Short after exact channel verification."""
    youtube = get_youtube_client()
    if "#shorts" not in title.lower() and "#shorts" not in description.lower():
        description = description.rstrip() + "\n\n#Shorts"
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or ["GK", "Tamil", "quiz", "general knowledge"],
            "categoryId": "27",
            "defaultLanguage": "ta",
            "defaultAudioLanguage": "ta",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]
