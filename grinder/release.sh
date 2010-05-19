#!/bin/bash

read -p "Build and release grinder (y/n)? "
if [ $REPLY == "y" ]; then
    tito tag
    git push
    git push --tags
    tito build --tgz
    tito build --srpm
    tito build --rpm
    scp /tmp/tito/grinder-*.rpm fedorapeople.org:./public_html/grinder/
    scp /tmp/tito/grinder-*.tar.gz fedorapeople.org:./public_html/grinder/
    scp /tmp/tito/noarch/grinder-*.rpm fedorapeople.org:./public_html/grinder/
fi


