FROM centos/httpd
MAINTAINER Pulp Team <pulp-list@redhat.com>

ADD rhel-pulp.repo /etc/yum.repos.d/rhel-pulp.repo

# We can't install or upgrade httpd on the docker hub build service because of
# this issue: https://github.com/docker/docker/issues/6980
# We have to force installing mod_ssl at a newer version than the httpd we
# have, since the older version is no longer available. It's ok for it to be
# broken, because we don't actually need to run httpd in this image.
RUN yum install -y yum-utils && yumdownloader mod_ssl && rpm -i --nodeps mod_ssl-* && yum clean all
RUN echo "" >> /etc/yum.conf && echo "exclude=httpd* iputils mod_ssl" >> /etc/yum.conf

RUN yum install -y epel-release && yum clean all

RUN yum update -y --skip-broken && \
    yum groupinstall -y pulp-server && \
    yum install -y pulp-python-plugins \
    findutils nmap-ncat mongodb && \
    yum clean all

ADD run.sh /run.sh
ADD validation_check.py /validation_check.py
ADD server.conf /etc/pulp/server.conf
RUN chgrp apache /etc/pulp/server.conf
USER apache

CMD ["/run.sh"]
