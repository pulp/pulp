#!/bin/sh

export HOSTNAME=`hostname`
export USERNAME='admin'
export PASSWORD='admin'
export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`

curl -s -k -H "Authorization: Basic $AUTH" https://${HOSTNAME}/pulp/api/v2/repositories/ | python -mjson.tool

