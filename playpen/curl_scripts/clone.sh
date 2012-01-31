#!/bin/sh
export USERNAME='admin'
export PASSWORD='admin'

if [ $# -lt 3 ]; then
    echo "Usage: $0 REPO CLONE_ID CLONE_NAME"
    exit 1
fi
REPO=$1
CLONE_ID=$2
CLONE_NAME=$3
echo "Will clone this repo <${REPO}> to this new cloned id <${CLONE_ID}>"

export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`

echo curl -k -H "Authorization: Basic $AUTH" -X POST -d "{\"clone_id\":\"${CLONE_ID}\",\"clone_name\":\"${CLONE_NAME}\",\"feed\":\"parent\"}" https://localhost/pulp/api/repositories/${REPO}/clone/
curl -k -H "Authorization: Basic $AUTH" -X POST -d "{\"clone_id\":\"${CLONE_ID}\",\"clone_name\":\"${CLONE_NAME}\",\"feed\":\"parent\"}" https://localhost/pulp/api/repositories/${REPO}/clone/

