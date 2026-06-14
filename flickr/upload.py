import os
import urllib3
from oauthlib.oauth1 import Client
from requests_toolbelt.multipart.encoder import MultipartEncoder
from urllib.parse import urlencode
from flickr.utils.url_lib_request import URLLibRequest
from flickr.utils.url_lib_response import URLLibResponse
import os
# — your creds here —
API_KEY = os.getenv("FLICKR_API_KEY", "")
API_SECRET = os.getenv("FLICKR_API_SECRET", "")
OAUTH_TOKEN = os.getenv("FLICKR_OAUTH_TOKEN", "")
OAUTH_TOKEN_SECRET = os.getenv("FLICKR_OAUTH_TOKEN_SECRET", "")

UPLOAD_URL = "https://up.flickr.com/services/upload/"

# 1) Prepare your text parameters
text_params = {
    "title": "My Test Upload",
    "description": "Signed parameters + multipart file",
    "is_public": "0",
    "is_friend": "0",
    "is_family": "0",
    "hidden": "2",
    "content_type": "1",
    "safety_level": "1",
    "tags": "test,python,flickr",
}

# 2) Create an OAuth1 client
oauth_client = Client(
    client_key=API_KEY,
    client_secret=API_SECRET,
    resource_owner_key=OAUTH_TOKEN,
    resource_owner_secret=OAUTH_TOKEN_SECRET,
)

# 3) Sign the URL **including** your URL-encoded text_params
body_for_signature = urlencode(text_params)
signed_url, oauth_headers, _ = oauth_client.sign(
    UPLOAD_URL,
    http_method="POST",
    body=body_for_signature,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)

# 4) Now build your multipart body (Flickr reads the file here)
file_path = os.path.join(os.path.dirname(__file__), "54004178222_44360a4956_o.jpg")
m = MultipartEncoder(
    fields={
        **text_params,
        "photo": (os.path.basename(file_path), open(file_path, "rb"), "image/jpeg"),
    }
)

# 5) Merge headers: the OAuth Authorization plus multipart Content-Type
headers = {
    "Authorization": oauth_headers["Authorization"],
    "Content-Type": m.content_type,
}

# 6) Send it
# http = urllib3.PoolManager()
# response = http.request("POST", signed_url, body=m.to_string(), headers=headers)  # raw multipart bytes
body = m.to_string()
response: URLLibResponse = URLLibRequest.post(
    url=signed_url,
    data=body,
    headers=headers,
)

print("Status code:", response.status)
print("Response body:", response.data.decode("utf-8"))
