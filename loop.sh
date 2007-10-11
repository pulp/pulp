#!/bin/bash
declare -i counter
counter=0
while [ "$counter" -lt 1000 ];do ./start-pulp.py; sleep 2; done
