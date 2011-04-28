#!/bin/sh

PULP_SERVER=`hostname`
USER="admin"
PASSWORD="admin"
export TASK_ID=""

function check_error {
    CHECK_ERROR=`echo $1 | python -c "import json,sys; data=json.load(sys.stdin); print data['exception']"`
    if [ "${CHECK_ERROR}" != "None" ] 
    then
        echo "Exception: ${CHECK_ERROR}"
        echo "Full status: $1"
        exit 1
    fi
}

function sync {
    SYNC_RETURN=`curl -s -k -u "${USER}:${PASSWORD}" --request POST --data '{}' --header 'accept:application/json' --header 'content-type: application/json' https://${PULP_SERVER}/pulp/api/repositories/$1/sync/`
    echo "SYNC_RETURN is <${SYNC_RETURN}>"
    check_error "${SYNC_RETURN}"
    export TASK_ID=`echo ${SYNC_RETURN} | python -c "import json,sys; data=json.load(sys.stdin); print data['id']"`
}

function sync_status {
    STATUS=`curl -s -k -u "${USER}:${PASSWORD}" https://${PULP_SERVER}/pulp/api/repositories/$1/sync/${TASK_ID}/`
    echo "Cancelling TASK_ID: <${TASK_ID}>"
    check_error "${STATUS}"
    echo "Repo <$1> is syncing.  Status = <${STATUS}>"
}

function sync_cancel {
    curl -k -u "${USER}:${PASSWORD}" --request DELETE https://${PULP_SERVER}/pulp/api/repositories/$1/sync/${TASK_ID}/
    STATUS=`curl -s -k -u "${USER}:${PASSWORD}" https://${PULP_SERVER}/pulp/api/repositories/$1/sync/${TASK_ID}/`
    echo "After Cancel of <${TASK_ID}> STATUS = <${STATUS}>"
    check_error "${STATUS}"
    echo "Repo <$1> sync has been cancelled.  Status = <${STATUS}>"
}

function sync_and_cancel {
    echo ""
    sync $1
    sync_status $1
    sync_cancel $1
}

while [ 1 ]; 
do
    sync_and_cancel $1
done


