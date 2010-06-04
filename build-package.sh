#!/bin/bash

cd $1
echo BUILDING $1
tito build --$2
