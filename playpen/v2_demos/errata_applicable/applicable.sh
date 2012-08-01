#!/bin/sh
export SERVER=127.0.0.1
export USERNAME='admin'
export PASSWORD='admin'

if [ $# -lt 2 ]; then
    echo "Usage: $0 ERRATA_ID CONSUMER_ID"
    exit 1
fi

export ERRATA_ID=$1
export CONSUMER_ID=$2

export UNITS="[{\"unit_key\": {\"id\": \"${ERRATA_ID}\"}, \"type_id\": \"erratum\"}]"
export CRITERIA="{\"sort\": [[\"id\", \"ascending\"]], \"filters\": {\"id\": {\"\$in\": [\"${CONSUMER_ID}\"]}}}"
export DATA="{\"units\": ${UNITS} , \"criteria\": ${CRITERIA} }"

URL=https://${SERVER}/pulp/api/v2/consumers/actions/content/applicability/

echo "Calling ${URL} with"
echo "${DATA}"
echo ""
echo "Result:"
curl -s -S -k -H "Authorization: Basic $AUTH" -X POST -d "${DATA}" ${URL} | python -mjson.tool 


