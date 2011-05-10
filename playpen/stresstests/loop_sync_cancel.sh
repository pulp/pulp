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
        #exit 1
    fi
}

function sync {
    if [ -z $1 ]
    then
        echo "No repo_id passed in"
        exit 1
    fi
    SYNC_RETURN=`curl -s -k -u "${USER}:${PASSWORD}" --request POST --data '{}' --header 'accept:application/json' --header 'content-type: application/json' https://${PULP_SERVER}/pulp/api/repositories/$1/sync/`
    echo "SYNC_RETURN is <${SYNC_RETURN}>"
    if [ "${SYNC_RETURN}" == "None" ]
    then
        echo "SYNC_RETURN is empty"
        exit 1
    fi
    check_error "${SYNC_RETURN}"
    export TASK_ID=`echo ${SYNC_RETURN} | python -c "import json,sys; data=json.load(sys.stdin); print data['id']"`
}

function sync_status {
    STATUS=`curl -s -k -u "${USER}:${PASSWORD}" https://${PULP_SERVER}/pulp/api/repositories/$1/sync/${TASK_ID}/`
    check_error "${STATUS}"
    echo -e "\tStatus of Task <${TASK_ID}> on repo <$1> is \n\t\t<${STATUS}>"
}

function sync_cancel {
    echo "Calling sync_cancel"
    curl -k -u "${USER}:${PASSWORD}" --request DELETE https://${PULP_SERVER}/pulp/api/repositories/$1/sync/${TASK_ID}/
    STATUS=`curl -s -k -u "${USER}:${PASSWORD}" https://${PULP_SERVER}/pulp/api/repositories/$1/sync/${TASK_ID}/`
    check_error "${STATUS}"
    echo -e "\tRepo <$1> sync_task <${TASK_ID}> has been cancelled.  Status = <${STATUS}>"
}

function sync_and_cancel {
    echo ""
    sync $1
    #sync_status $1
    sync_cancel $1
    #sync_status $1
}


if [ -z $1 ]
then
    echo "Usage:  $0 <repo_id>"
    exit 1
fi

while [ 1 ]; 
do
    sync_and_cancel $1
done


