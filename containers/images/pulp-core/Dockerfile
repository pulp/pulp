FROM centos:7

ARG PLUGINS=""

RUN echo "tsflags=nodocs" >> /etc/yum.conf && \
		yum -y install epel-release centos-release-scl && \
		yum -y install wget git rh-python36-python-pip && \
		yum clean all

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV PYTHONUNBUFFERED=0
ENV DJANGO_SETTINGS_MODULE=pulpcore.app.settings

RUN mkdir -p /etc/pulp

RUN scl enable rh-python36 'pip install gunicorn'
RUN scl enable rh-python36 'pip install pulpcore'
RUN scl enable rh-python36 'pip install $PLUGINS'

COPY container-assets/settings.py /etc/pulp/settings.py
RUN echo "SECRET_KEY = '`cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50`'" >> /etc/pulp/settings.py

RUN scl enable rh-python36 "pulp-manager makemigrations pulp_app"
RUN scl enable rh-python36 "pulp-manager makemigrations $PLUGINS"
RUN scl enable rh-python36 "pulp-manager collectstatic --noinput"

COPY container-assets/wait_on_postgres.py /usr/bin/wait_on_postgres.py
COPY container-assets/wait_on_database_migrations.sh /usr/bin/wait_on_database_migrations.sh
COPY container-assets/migrate_pulp.sh /usr/bin/migrate_pulp.sh
COPY container-assets/pulp-core /usr/bin/pulp-core

RUN echo "scl enable rh-python36 \"pulp-manager migrate --noinput $PLUGINS\"" >> /usr/bin/migrate_pulp.sh

CMD ["/usr/bin/pulp-core"]
