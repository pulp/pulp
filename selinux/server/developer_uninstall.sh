NAME="pulp-server"
./dev_setup_label.sh clean
./uninstall.sh 
if [ "$?" -ne "0" ]; then
    echo "Error uninstalling selinux policy"
    exit 1
fi
/usr/sbin/semodule -l | grep ${NAME}
if [ "$?" -eq "0" ]; then
    echo "WARNING: ${NAME} selinux policy is still loaded"
    exit 1
fi
./relabel.sh
