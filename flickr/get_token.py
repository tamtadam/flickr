from requests_oauthlib import OAuth1Session
import webbrowser
import os


import flickrapi
 
api_key = u'd'
api_secret = u'd'
 
flickr = flickrapi.FlickrAPI(api_key, api_secret)
flickr.authenticate_via_browser(perms='write')



API_KEY = os.getenv("FLICKR_API_KEY", "d")
API_SECRET = os.getenv("FLICKR_API_SECRET", "d")

# Flickr OAuth-végpontok
REQUEST_TOKEN_URL = "https://www.flickr.com/services/oauth/request_token"
AUTHORIZE_URL = "https://www.flickr.com/services/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.flickr.com/services/oauth/access_token"

# A callback URL, ahová a felhasználó visszakerül a böngészőben
# Ha teszteléshez lokális scriptet használsz, állítsd pl. erre:
OAUTH_CALLBACK = "oob"  # out-of-band – terminálból kéred be kézzel a verifier-t


# 2:::::::::::::::::
# OAuth1Session létrehozása a consumer adatokkal és callback-kel
oauth = OAuth1Session(API_KEY, client_secret=API_SECRET, callback_uri=OAUTH_CALLBACK)

# Kérés a request token-ért
fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")

print("Request Token begyűjtve:")
print("  - oauth_token:        ", resource_owner_key)
print("  - oauth_token_secret: ", resource_owner_secret)


# Az authorize URL összeállítása
authorization_url = oauth.authorization_url(AUTHORIZE_URL)
print("Kérlek nyisd meg a következő URL-t a böngésződben, és engedélyezd az alkalmazást:")
print(authorization_url)

verifier = input("Add meg az oauth_verifier kódot: ")

# Új OAuth1Session az eddigi credential-ekkel és a verifier-rel
oauth = OAuth1Session(
    API_KEY,
    client_secret=API_SECRET,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)

# Kérés az access token-ért
access_token_response = oauth.fetch_access_token(ACCESS_TOKEN_URL)
access_token = access_token_response.get("oauth_token")
access_token_secret = access_token_response.get("oauth_token_secret")

print("Access Token begyűjtve:")
print("  - oauth_token:        ", access_token)
print("  - oauth_token_secret: ", access_token_secret)
