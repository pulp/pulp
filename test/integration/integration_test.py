import os


# Configure pulp repo
os.system("wget -O /etc/yum.repos.d/pulp-devel.repo http://mmccune.fedorapeople.org/pulp/fedora/pulp.repo")

# Install pulp
os.system("yum clean all")
os.system("yum -y install pulp pulp-tools python-nose")

# start httpd and mongo
os.system("/sbin/service httpd restart")
os.system("/sbin/service mongod restart")
os.system("/sbin/service mongod restart")

code = os.system("cd /root/devel/pulp/test/;nosetests")
exit(code)




