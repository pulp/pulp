import os
from distutils.sysconfig import get_python_lib

# Configure pulp repo
os.system("wget -O /etc/yum.repos.d/pulp-devel.repo http://mmccune.fedorapeople.org/pulp/fedora/pulp.repo")

# Install pulp
os.system("yum clean all")
os.system("rpm -e pulp pulp-tools python-nose")
os.system("yum -y install pulp pulp-tools python-nose")

# start httpd and mongo
os.system("/sbin/service httpd restart")
os.system("/sbin/service mongod restart")
os.system("/sbin/service mongod restart")

pylib = get_python_lib()
code = os.system("cd %s/pulp/test/ws/;nosetests" % pylib)
exit(code)




