#!/bin/sh
export SERVER=127.0.0.1
export USERNAME='admin'
export PASSWORD='admin'

if [ $# -lt 4 ]; then
    echo "Usage: $0 ERRATA_ID CONSUMER_ID_PREFIX LOWER_LIMIT UPPER_LIMIT"
    exit 1
fi

export ERRATA_ID=$1
export CONSUMER_ID_PREFIX=$2
export LOWER_LIMIT=$3
export UPPER_LIMIT=$4
export CONSUMER_ID_LOWER=${CONSUMER_ID_PREFIX}${LOWER_LIMIT}
export CONSUMER_ID_UPPER=${CONSUMER_ID_PREFIX}${UPPER_LIMIT}

export UNITS="[{\"unit_key\": {\"id\": \"${ERRATA_ID}\"}, \"type_id\": \"erratum\"}]"
export CRITERIA="{\"sort\": [[\"id\", \"ascending\"]], \"filters\": {\"id\": {\"\$gte\": \"${CONSUMER_ID_LOWER}\", \"\$lte\": \"${CONSUMER_ID_UPPER}\"}}}"
export DATA="{\"units\": ${UNITS} , \"criteria\": ${CRITERIA} }"

URL=https://${SERVER}/pulp/api/v2/consumers/actions/content/applicability/

echo ""
echo ""
echo "Calling ${URL} with"
echo "${DATA}"
echo ""
echo ""
echo "Result:"
curl -s -S -k -H "Authorization: Basic $AUTH" -X POST -d "${DATA}" ${URL} | ./display_results.py

