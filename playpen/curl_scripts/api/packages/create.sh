#!/bin/sh
export USERNAME='admin'
export PASSWORD='admin'

export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`
export PKG_NAME="test_api_example_package_name_$RANDOM"
export EPOCH="0"
export VER="1"
export REL="1"
export ARCH="i386"
export DESCR="Description for $PKG_NAME"
export SUM_TYPE="sha256"
export SUM="6f619869dd4b83c12460558d85d14590f638a72717824136baacf6538fa114bb"
export FILENAME="$PKG_NAME.rpm"


export ARGS_DATA="\"name\": \"${PKG_NAME}\", \"epoch\": \"${EPOCH}\", \"version\": \"${VER}\", \"release\": \"${REL}\", \"arch\": \"${ARCH}\", \"description\": \"${DESCR}\", \"checksum\": \"${SUM}\", \"checksum_type\": \"${SUM_TYPE}\", \"filename\": \"${FILENAME}\""

curl -s -S -k -H "Authorization: Basic $AUTH" -X PUT -d "{${ARGS_DATA}}" https://localhost/pulp/api/packages/ | python -mjson.tool 

