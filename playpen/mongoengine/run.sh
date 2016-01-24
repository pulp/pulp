#!/usr/bin/env bash

DBNAME="28upgradedb"
LINKS="--link $DBNAME:db"
DUMPDIR=`pwd`/dump
MOUNTS="-v $DUMPDIR:/dump/:ro -v /dev/log:/dev/log"
LOGFILE=upgrade_validation-`date -u +%Y%m%d%H%M%S`.log

docker run -d --name $DBNAME -v /dev/log:/dev/log pulp/mongodb
docker run -it --rm $LINKS $MOUNTS pulp/28upgradetest | tee $LOGFILE
docker stop $DBNAME
docker rm $DBNAME
