#!/bin/sh
export USERNAME='admin'
export PASSWORD='admin'

export AUTH=`python -c "import base64; print base64.encodestring(\"${USERNAME}:${PASSWORD}\")[:-1]"`

if [ $# -eq 1 ]; then
    DIST_ID=$1
    echo "curl -s -k -H \"Authorization: Basic $AUTH\"  https://localhost/pulp/api/distributions/${DIST_ID}/ | python -mjson.tool"
    curl -s -k -H "Authorization: Basic $AUTH"  https://localhost/pulp/api/distributions/${DIST_ID}/ | python -mjson.tool
else
    echo "curl -s -k -H \"Authorization: Basic $AUTH\"  https://localhost/pulp/api/distributions/ | python -mjson.tool"
    curl -s -k -H "Authorization: Basic $AUTH"  https://localhost/pulp/api/distributions/ | python -mjson.tool
fi

#curl -k -H "Authorization: Basic $AUTH" -X POST -d "{\"clone_id\":\"${CLONE_ID}\",\"clone_name\":\"${CLONE_NAME}\",\"feed\":\"parent\"}" https://localhost/pulp/api/repositories/${REPO}/clone/

