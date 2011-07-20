NAME="pulp"
install -p -m 644 ${NAME}.pp /etc/selinux/targeted/${NAME}.pp
semodule -i /etc/selinux/targeted/${NAME}.pp

