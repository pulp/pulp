#!/bin/bash

echo "docs.pulpproject.org,8.43.85.236 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGXG+8vjSQvnAkq33i0XWgpSrbco3rRqNZr0SfVeiqFI7RN/VznwXMioDDhc+hQtgVhd6TYBOrV07IMcKj+FAzg=" >> /home/travis/.ssh/known_hosts
chmod 644 /home/travis/.ssh/known_hosts

cd .travis
export PYTHONUNBUFFERED=1

eval "$(ssh-agent -s)" #start the ssh agent
ssh-add ~/.ssh/pulp-infra

python3 docs-builder.py --release 2-master