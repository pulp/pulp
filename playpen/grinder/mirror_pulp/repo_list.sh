#!/bin/sh
export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`
curl -s -k -H "Authorization: Basic $AUTH" https://localhost/pulp/api/repositories/ -o repo_list.json

