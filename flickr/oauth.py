from requests_oauthlib import OAuth1Session
import os
API_KEY = os.getenv("FLICKR_API_KEY", "")
API_SECRET = os.getenv("FLICKR_API_SECRET", "")

REQUEST_TOKEN_URL = "https://www.flickr.com/services/oauth/request_token"
AUTHORIZE_URL = "https://www.flickr.com/services/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.flickr.com/services/oauth/access_token"

# Step 1: Get request token
oauth = OAuth1Session(API_KEY, client_secret=API_SECRET, callback_uri="oob")
fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")

print("Request Token:", resource_owner_key)
print("Request Token Secret:", resource_owner_secret)

# Step 2: Get user authorization
auth_url = f"{AUTHORIZE_URL}?oauth_token={resource_owner_key}&perms=write"
print("Go to this URL in a browser and authorize the app:")
print(auth_url)

# Step 3: Get verifier code from user
verifier = input("Enter the verifier code: ")

# Step 4: Get access token
oauth = OAuth1Session(
    API_KEY,
    client_secret=API_SECRET,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)

access_token_response = oauth.fetch_access_token(ACCESS_TOKEN_URL)
oauth_token = access_token_response.get("oauth_token")
oauth_token_secret = access_token_response.get("oauth_token_secret")

print("\n✅ Access token and secret:")
print("OAUTH_TOKEN =", oauth_token)
print("OAUTH_TOKEN_SECRET =", oauth_token_secret)
