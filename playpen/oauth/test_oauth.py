import httplib
import time
import oauth2 as oauth 

CONSUMER_KEY = 'example-key'
CONSUMER_SECRET = 'example-secret'
URL = "https://localhost/pulp/api/v2/users/"

# Setup a standard HTTPSConnection object
connection = httplib.HTTPSConnection("localhost", "443")
# Create an OAuth Consumer object 
consumer = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)

# Formulate a OAuth request with the embedded consumer with key/secret pair
oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method="GET", http_url=URL)
# Sign the Request.  This applies the HMAC-SHA1 hash algorithm
oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)

# Add the pulp-user header variable
headers = dict(oauth_request.to_header().items() + {'pulp-user':'admin'}.items())
# Actually make the request
connection.request("GET", "/pulp/api/v2/users/", headers=headers) 
# Get the response and read the output
response = connection.getresponse()
output = response.read()
print output
