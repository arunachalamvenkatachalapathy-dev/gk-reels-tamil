import os
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("google", types.ModuleType("google"))
sys.modules.setdefault("google.oauth2", types.ModuleType("google.oauth2"))
class FakeCredentials:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
sys.modules.setdefault("google.oauth2.credentials", types.SimpleNamespace(Credentials=FakeCredentials))
sys.modules.setdefault("googleapiclient", types.ModuleType("googleapiclient"))
sys.modules.setdefault("googleapiclient.discovery", types.SimpleNamespace(build=None))
sys.modules.setdefault("googleapiclient.http", types.SimpleNamespace(MediaFileUpload=object))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import upload_youtube

class ChannelGuardTests(unittest.TestCase):
    def test_wrong_expected_channel_stops_before_client_build(self):
        with patch.dict(os.environ, {"YT_CHANNEL_ID": "UCwrong"}, clear=True), patch.object(upload_youtube, "build") as build:
            with self.assertRaisesRegex(RuntimeError, "YT_CHANNEL_ID"):
                upload_youtube.get_youtube_client()
            build.assert_not_called()

    def test_oauth_channel_mismatch_fails_closed(self):
        channels = types.SimpleNamespace(list=lambda **kwargs: types.SimpleNamespace(execute=lambda: {"items": [{"id": "UCwrong"}]}))
        client = types.SimpleNamespace(channels=lambda: channels)
        with patch.dict(os.environ, {"YT_CHANNEL_ID": "UC5ZLfNHUI4z92IW69KVTGxg", "YT_CLIENT_ID": "id", "YT_CLIENT_SECRET": "secret", "YT_REFRESH_TOKEN": "refresh"}, clear=True), patch.object(upload_youtube, "build", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "OAuth identity mismatch"):
                upload_youtube.get_youtube_client()

    def test_expected_channel_is_accepted(self):
        expected = "UC5ZLfNHUI4z92IW69KVTGxg"
        channels = types.SimpleNamespace(list=lambda **kwargs: types.SimpleNamespace(execute=lambda: {"items": [{"id": expected}]}))
        client = types.SimpleNamespace(channels=lambda: channels)
        with patch.dict(os.environ, {"YT_CHANNEL_ID": expected, "YT_CLIENT_ID": "id", "YT_CLIENT_SECRET": "secret", "YT_REFRESH_TOKEN": "refresh"}, clear=True), patch.object(upload_youtube, "build", return_value=client):
            self.assertIs(upload_youtube.get_youtube_client(), client)

if __name__ == "__main__":
    unittest.main()
