#!/bin/sh
# this assumes that vda has only one partition, which contains an ext filesystem

# remote-control fdisk to blindly delete and re-create the first partition on vda
# (d)elete the only partition, create a (n)ew (p)rimary partition numbered (1),
# accept some defaults (the two newlines), (w)rite the new table
sudo fdisk /dev/vda <<EOF
d
n
p
1


w
EOF

# refresh partition tables
sudo partprobe

# fill the new space if needed
sudo resize2fs /dev/vda1
