# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains distributor plugins and functionality for the Pulp plugin testing harness.
"""

import datetime
import logging
import os
import shutil
import time

from pulp.server.plugins.plugins.distributor import Distributor
from pulp.server.plugins.plugins.model import PublishReport

# -- constants ----------------------------------------------------------------

# Until Pulp injects the logger, grab one from the Pulp namespace to use its
# file location
_LOG = logging.getLogger(__name__)
_LOG.addHandler(logging.FileHandler('/var/log/pulp/harness-distributor.log'))

ACCEPTABLE_CONFIG_KEYS = ['write_files', 'publish_dir']

# -- plugins ------------------------------------------------------------------

class HarnessDistributor(Distributor):

    @classmethod
    def metadata(cls):
        return {
            'id'           : 'harness_distributor',
            'display_name' : 'Test Harness Distributor',
            'types'        : ['harness_type_one', 'harness_type_two']
        }

    def validate_config(self, repo, config):

        # Simply make sure that everything passed in the config is expected.
        # This lets the user simulate an invalid config by passing any other
        # key into the config.
        for key in config.repo_plugin_config:
            if key not in ACCEPTABLE_CONFIG_KEYS:
                return False
            if config.repo_plugin_config.get(key) is None:
                return False
        return True

    def publish_repo(self, repo, publish_conduit, config):

        start = datetime.datetime.now()

        units = publish_conduit.get_units()

        write_files = config.get('write_files').lower() == 'true'
        publish_dir = config.get('publish_dir', None)

        if write_files and publish_dir is None:
            raise Exception('Incorrect configuration for the distributor; write_files was specified but publish_dir was not')

        _LOG.info('Publishing repository [%s]' % repo.id)
        if write_files:
            _LOG.info('Unit files will be written to [%s]' % publish_dir)
        else:
            _LOG.info('Files will not be written as part of the publish')

        if write_files:
            if os.path.exists(publish_dir):
                shutil.rmtree(publish_dir)
            os.makedirs(publish_dir)

            for u in units:
                file_name = os.path.basename(u.storage_path)
                publish_file_name = os.path.join(publish_dir, file_name)
                shutil.copy(u.storage_path, publish_file_name)

        # Fake a slow publish if one is requested
        publish_delay_in_seconds = config.get('publish_delay_in_seconds', None)
        if publish_delay_in_seconds is not None:
            _LOG.info('Faking a long publish with delay of [%s] seconds' % publish_delay_in_seconds)
            time.sleep(int(publish_delay_in_seconds))

        # Exercise the scratchpad with a simple counter of all syncs ever
        all_publish_count = publish_conduit.get_scratchpad()
        if all_publish_count is None:
            all_publish_count = 1
        else:
            all_publish_count = int(all_publish_count) + 1
        publish_conduit.set_scratchpad(all_publish_count)

        end = datetime.datetime.now()
        ellapsed_in_seconds = (end - start).seconds

        summary = 'Publish Successful'

        details  = 'Publish Summary\n'
        details += 'Ellapsed time in seconds:  %d\n' % ellapsed_in_seconds
        details += 'Number of units published: %d\n' % len(units)
        details += 'Files written:             %s\n' % write_files
        if write_files:
            details += 'Publish directory:         %s\n' % publish_dir
        details += 'Global publish count:      %d' % all_publish_count

        return publish_conduit.build_success_report(summary, details)
    