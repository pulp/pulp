#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# Use this bash script to run argument 1 on each setup.py in this project

for setup in `find . -name setup.py`; do
    pushd `dirname $setup`;
    python setup.py "$@";
    popd;
done;
