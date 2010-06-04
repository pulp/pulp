#!/bin/bash

rm -rf /tmp/tito/*
find -name "*.spec" -printf "%h"\\n |xargs -n 1 -I foo ./build-package.sh foo rpm
