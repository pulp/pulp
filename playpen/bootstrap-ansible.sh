#!/bin/sh

# minimal bootstrapping before kicking off ansible:
#  install only what ansible needs to survive, or doesn't know how to do
sudo dnf -y install python2 python2-dnf libselinux-python
