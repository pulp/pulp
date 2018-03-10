import requests
import os

GITHUB_USER_ID = 37230624
BASE_URL = 'https://api.github.com'

PULL_REQUEST = os.environ['TRAVIS_PULL_REQUEST']
REPOSITORY = os.environ['TRAVIS_REPO_SLUG']
TEST = os.environ['TEST']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']


def request(query=None, method="GET", json=None, data=None, headers=None, params=None):
    """
    Queries like /repos/:id needs to be appended to the base URL,
    Queries like https://raw.githubusercontent.com need not.
    full list of kwargs see http://docs.python-requests.org/en/master/api/#requests.request
    """

    if query[0] == "/":
        query = BASE_URL + query

    kwargs = {
        "auth": "token {}".format(GITHUB_TOKEN),
        "json": json if json else None,
        "data": data if data else None,
        "headers": headers if headers else None,
        "params": params if params else None,
    }
    return requests.request(method, query, **kwargs)


def create_comment(pr_number, comment):
    """
    Create a new comment only if one does not already exist
    """

    query = "/repos/{}/issues/{}/comments"
    query = query.format(REPOSITORY, str(pr_number))
    comments = request(query).json()

    for old_comment in comments:
        if old_comment["user"]["id"] == GITHUB_USER_ID:
            # there's already a comment. just exit
            return

    request(query=query, method='POST', json={"body": comment})


# only comment the warning for pulp_file builds
if PULL_REQUEST != 'false':
    comment = "Woof! One of the pulp_file builds failed. Please check the \
            pulp_file build jobs in Travis before merging this PR."
    create_comment(PULL_REQUEST, comment)
