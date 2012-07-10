:orphan:

CentOS Support
==============

.. _centos-build-qpid-rpms:

Building QPID RPMs
------------------

The process of building the QPID RPMs on CentOS is relatively straight forward.
There are a few packages that must be installed for satisfy Pulp dependencies.
These instructions outline the approach of installing and building the source
RPMs.

In order to get all of the dependencies needed, the
"Extra Packages for Enterprise Linux version 5 (EPEL5) repository" is required.
Instructions on how to do so can be found at: `<http://fedoraproject.org/wiki/EPEL/FAQ#Using_EPEL>`_

1. Install rpmbuild:

::

    $ yum install rpm-build

2. Create a mockbuild user:

::

    $ adduser mockbuild

3. Install the source RPMs (the latest can be found at: `<ftp://ftp.redhat.com/pub/redhat/linux/enterprise/5Server/en/RHEMRG/SRPMS/>`_):

::

    $ rpm -i ftp://ftp.redhat.com/pub/redhat/linux/enterprise/5Server/en/RHEMRG/SRPMS/amqp-1.0.750054-1.el5.src.rpm
    $ rpm -i ftp://ftp.redhat.com/pub/redhat/linux/enterprise/5Server/en/RHEMRG/SRPMS/python-qpid-0.7.946106-15.el5.src.rpm
    $ rpm -i ftp://ftp.redhat.com/pub/redhat/linux/enterprise/5Server/en/RHEMRG/SRPMS/qpid-cpp-mrg-0.7.946106-28.el5.src.rpm

4. Install extra dependencies:

::

    $ yum install gcc-c++ boost-devel doxygen e2fsprogs-devel libtool ruby cyrus-sasl-devel \
                  libibverbs-devel librdmacm-devel nss-devel nspr-devel xqilla-devel xerces-c-devel \
                  openais-devel cman-devel python-devel ruby-devel swig db4-devel libaio-devel

5. Build the RPMs:

::

    $ cd /usr/src/redhat
    $ rpmbuild -bb SPECS/amqp.spec
    $ rpmbuild -bb SPECS/python-qpid.spec
    $ rpmbuild -bb SPECS/qpid-cpp-mrg.spec

The build produces the following (noarch) RPMs:

* amqp-1.0.750054-1.noarch.rpm
* python-qpid-0.7.946106-15.noarch.rpm

The build produces the following RPMs:

* qpid-cpp-client-0.7.946106-28.x86_64.rpm
* qpid-cpp-client-devel-0.7.946106-28.x86_64.rpm
* qpid-cpp-client-devel-docs-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-devel-0.7.946106-28.x86_64.rpm
* qmf-0.7.946106-28.x86_64.rpm
* qmf-devel-0.7.946106-28.x86_64.rpm
* ruby-qmf-0.7.946106-28.x86_64.rpm
* qpid-cpp-client-rdma-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-rdma-0.7.946106-28.x86_64.rpm
* qpid-cpp-client-ssl-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-ssl-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-xml-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-cluster-0.7.946106-28.x86_64.rpm
* qpid-cpp-server-store-0.7.946106-28.x86_64.rpm
* rh-qpid-cpp-tests-0.7.946106-28.x86_64.rpm