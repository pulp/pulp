#!/bin/sh
mongo pulp_database --eval "db.task_snapshots.drop();"
