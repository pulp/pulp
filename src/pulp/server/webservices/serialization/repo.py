
"""
Module for repo serialization.
"""

from pulp.server.cds import round_robin
from pulp.server.webservices import http

# contstants -------------------------------------------------------------------

# XXX these shouls be stored in a common module
API_HREF = '/pulp/api'
API_V2_HREF = API_HREF + '/v2'

REPO_URI_PATH = '/pub/repos'

COLLECTION_HREF = API_HREF + '/repositories'
RESOURCE_HREF = COLLECTION_HREF + '/%s'

# repo serialization api -------------------------------------------------------

def href(repo):
    href = RESOURCE_HREF % repo['id']
    return ensure_ending_slash(href)


def uri(repo):
    # not published: no repo uri
    if not repo['publish']:
        return None
    # use cds uri first
    cds = round_robin._find_association(repo['id'])
    if cds is not None:
        return cds['next_permutation'][0]
    # no cds association: build local uri
    request_uri = http.request_url()
    uri_prefix = request_uri.split(API_HREF)[0]
    uri = '/'.join((uri_prefix, REPO_URI_PATH, repo['id']))
    return ensure_ending_slash(uri)


# utility methods --------------------------------------------------------------

# XXX this should be stored in a utility module
def ensure_ending_slash(uri_or_path):
    if not uri_or_path.endswith('/'):
        uri_or_path += '/'
    return uri_or_path
