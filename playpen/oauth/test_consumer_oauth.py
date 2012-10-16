'''
This script tests oauth authentication for consumers. 
Running this script should show 4 test runs in the output, all of which should result in "Invalid OAuth Credentials" response.
Now register a consumer with id 'test-consumer' and run the test again. There should not be any invalid credential messages. 
This script also unregisters 'test-consumer' at the end, so make sure you register it again before running the script. 
'''


import httplib
import oauth2 as oauth 

CONSUMER_KEY = 'example-key'
CONSUMER_SECRET = 'example-secret'
CONSUMER_URL = "https://localhost/pulp/api/v2/consumers/test-consumer/"
REPOSITORIES_URL = "https://localhost/pulp/api/v2/repositories/"

# Setup a standard HTTPSConnection object
connection = httplib.HTTPSConnection("localhost", "443")
# Create an OAuth Consumer object 
consumer = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)

# Test 1

print "\n --- Test1 ---"
# Formulate a OAuth request with the embedded consumer with key/secret pair
oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method="GET", http_url=CONSUMER_URL)
# Sign the Request.  This applies the HMAC-SHA1 hash algorithm
oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)
# Add the pulp-user header variable
headers = dict(oauth_request.to_header().items() + {'pulp-user':'test-consumer'}.items())
print "\nHEADERS : %s", headers

# Actually make the request
connection.request("GET", "/pulp/api/v2/consumers/test-consumer/", headers=headers) 

# Get the response and read the output
response = connection.getresponse()
output = response.read()
print "\nRESPONSE : %s", output


# Test 2

print "\n --- Test2 ---"
oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method="PUT", http_url=CONSUMER_URL)
oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)
headers = dict(oauth_request.to_header().items() + {'pulp-user':'test-consumer'}.items())
print "\nHEADERS : %s", headers
connection.request("PUT", "/pulp/api/v2/consumers/test-consumer/", headers=headers) 
response = connection.getresponse()
output = response.read()
print "\nRESPONSE : %s", output


# Test 3

print "\n --- Test3 ---"
oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method="GET", http_url=REPOSITORIES_URL)
oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)
headers = dict(oauth_request.to_header().items() + {'pulp-user':'test-consumer'}.items())
print "\nHEADERS : %s", headers
connection.request("GET", "/pulp/api/v2/repositories/", headers=headers) 
response = connection.getresponse()
output = response.read()
print "\nRESPONSE : %s", output


# Test 4

print "\n --- Test4 ---"
oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method="DELETE", http_url=CONSUMER_URL)
oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)
headers = dict(oauth_request.to_header().items() + {'pulp-user':'test-consumer'}.items())
print "\nHEADERS : %s", headers
connection.request("DELETE", "/pulp/api/v2/consumers/test-consumer/", headers=headers) 
response = connection.getresponse()
output = response.read()
print "\nRESPONSE : %s", output


