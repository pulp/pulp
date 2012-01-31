#!/bin/sh

kill -0 $1
while [ $? -eq 0 ] 
do
    pmap -d $1 | tail -n 1
    sleep 60
    date
    kill -0 $1
done

