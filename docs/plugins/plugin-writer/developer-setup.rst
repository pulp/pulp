Developer Setup
===============

Each release of ``pulpcore`` on PyPI is released as a Vagrant box on `vagrantcloud.com <https://app.vagrantup.com/pulp/boxes/pulpcore>`_.
To get started, you need to install Vagrant. You can refer `developer installation instructions <https://docs.pulpproject.org/dev-guide/contributing/dev_setup.html#vagrant>`_.
For backends, you can opt for either `libvirt <https://docs.pulpproject.org/dev-guide/contributing/dev_setup.html#prerequisites-for-libvirt>`_ or `Virtualbox <https://www.virtualbox.org/wiki/Downloads>`_.

One can use this :download:`Vagrantfile <Vagrantfile>` as a starting point and modify it as necessary.

Start up the ``pulpcore`` Vagrant box::

  $ vagrant up

Once the box is downloaded and booted an ssh connection can be established with a forward tunnel for port 8000::

  $ vagrant ssh -- -L 8000:localhost:8000

Become user ``pulp``, activate the ``pulpenv`` virtual env, and start the webserver::

  $ sudo su - pulp
  $ source pulpvenv/bin/activate
  $ pulp-manager runserver

The browsable API can be accessed at http://localhost:8000/api/v3/ on the host machine.