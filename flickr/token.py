from pathlib import Path
import json

TOKEN_FILE = Path.home() / ".flickr_tokens.json"


class FlickrToken:
    """
    Class to handle Flickr API tokens.
    """

    def __init__(self, api_key: str, api_secret: str, oauth_token: str, oauth_token_secret: str, token_file=TOKEN_FILE):
        self.token_file = token_file
        self.tokens = self.load_tokens()
        if not self.tokens:
            self.set_token(api_key=api_key, api_secret=api_secret, oauth_token=oauth_token, oauth_token_secret=oauth_token_secret)
        self.oauth_token: str = self.tokens.get("oauth_token", oauth_token)
        self.oauth_token_secret: str = self.tokens.get("oauth_token_secret", oauth_token_secret)
        self.api_key: str = self.tokens.get("api_key", api_key)
        self.api_secret: str = self.tokens.get("api_secret", api_secret)

    def load_tokens(self):
        """
        Load tokens from the specified file.
        """
        if not self.token_file.exists():
            return {}
        with open(self.token_file, "r") as f:
            return json.load(f)

    def save_tokens(self):
        """
        Save tokens to the specified file.
        """
        with open(self.token_file, "w") as f:
            json.dump(self.tokens, f)

    def set_token(self, api_key: str, api_secret: str, oauth_token: str, oauth_token_secret: str):
        """
        Set a token by key.
        """
        self.tokens["oauth_token"] = oauth_token
        self.tokens["oauth_token_secret"] = oauth_token_secret
        self.tokens["api_key"] = api_key
        self.tokens["api_secret"] = api_secret
        self.save_tokens()
