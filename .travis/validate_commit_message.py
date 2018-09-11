import re
import requests
import subprocess
import sys

KEYWORDS = ['fixes', 'closes', 're', 'ref']
NO_ISSUE = '#noissue'
STATUSES = ['NEW', 'ASSIGNED', 'POST']

sha = sys.argv[1]
message = subprocess.check_output(['git', 'log', '--format=%B', '-n 1', sha]).decode('utf-8')


def check_status(issue):
    response = requests.get('https://pulp.plan.io/issues/{}.json'.format(issue))
    response.raise_for_status()
    bug_json = response.json()
    status = bug_json['issue']['status']['name']
    if status not in STATUSES:
        sys.exit("Error: issue #{issue} has invalid status of {status}. Status must be one of "
                 "{statuses}.".format(issue=issue, status=status, statuses=", ".join(STATUSES)))


print("Checking commit message for {sha}.".format(sha=sha[0:7]))

# validate the issue attached to the commit
if NO_ISSUE in message:
    print("Commit {sha} has no issue attached. Skipping issue check".format(sha=sha[0:7]))
else:
    regex = r'(?:{keywords})[\s:]+#(\d+)'.format(keywords=('|').join(KEYWORDS))
    pattern = re.compile(regex)

    issues = pattern.findall(message)

    if issues:
        for issue in pattern.findall(message):
            check_status(issue)
    else:
        sys.exit("Error: no attached issues found for {sha}. If this was intentional, add "
                 " '{tag}' to the commit message.".format(sha=sha[0:7], tag=NO_ISSUE))

print("Commit message for {sha} passed.".format(sha=sha[0:7]))
