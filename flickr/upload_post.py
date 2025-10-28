import urllib3
from oauthlib.oauth1 import Client
from urllib.parse import parse_qs
import os

API_KEY = os.getenv("FLICKR_API_KEY", "")
API_SECRET = os.getenv("FLICKR_API_SECRET", "")
oauth_token = os.getenv("FLICKR_OAUTH_TOKEN", "")
oauth_token_secret = os.getenv("FLICKR_OAUTH_TOKEN_SECRET", "")
# Kérés urllib3-mal
http = urllib3.PoolManager()

from oauthlib.oauth1 import Client as OAuth1Client

# Új OAuth1 Client végleges tokenekkel
client = OAuth1Client(
    client_key=API_KEY, client_secret=API_SECRET, resource_owner_key=oauth_token, resource_owner_secret=oauth_token_secret
)

# Példa: flickr.test.login hívás
REST_ENDPOINT = "https://api.flickr.com/services/rest"
params = {
    "method": "flickr.test.login",
    "format": "json",
    "nojsoncallback": "1",
}

# A teljes URL-hez fűzd hozzá a query stringet
from urllib.parse import urlencode

url_with_qs = REST_ENDPOINT + "?" + urlencode(params)

# Aláírás generálása
uri, headers, body = client.sign(url_with_qs, http_method="GET")

# GET kérés
response = http.request("GET", uri, headers=headers)
print(response.data.decode("utf-8"))
