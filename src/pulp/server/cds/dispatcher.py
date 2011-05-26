#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

'''
Contains classes that are used to send messages to CDS instances.
'''

# Python
import logging
import sys

# 3rd Party
from gofer.messaging.dispatcher import DispatchError
from gofer.messaging.policy import RequestTimeout, NotAuthorized

# Pulp
from pulp.server import config, constants
from pulp.server.agent import CdsAgent


log = logging.getLogger(__name__)


# -- exceptions -------------------------------------------------------------------

class CdsDispatcherException(Exception):
    '''
    Base class for all dispatcher-related exceptions.
    '''
    def __init__(self, wrapped_exception):
        Exception.__init__(self)
        self.wrapped_exception = wrapped_exception

    def __repr__(self):
        return self.wrapped_exception.__repr__()

class CdsTimeoutException(CdsDispatcherException):
    '''
    Exception to indicate the remote method call on the CDS timed out.
    '''
    def __init__(self, wrapped_exception):
        CdsDispatcherException.__init__(self, wrapped_exception)

class CdsCommunicationsException(CdsDispatcherException):
    '''
    General exception for any error that came out of the underlying communications framework.
    '''
    def __init__(self, wrapped_exception):
        CdsDispatcherException.__init__(self, wrapped_exception)

class CdsAuthException(CdsDispatcherException):
    '''
    General exception for any authorization error that came out of the
    underlying communications framework.
    '''
    def __init__(self, wrapped_exception):
        CdsDispatcherException.__init__(self, wrapped_exception)

class CdsMethodException(CdsDispatcherException):
    '''
    General exception for any error that was raised by the CDS execution of pulp code.
    '''
    def __init__(self, wrapped_exception):
        CdsDispatcherException.__init__(self, wrapped_exception)

# -- dispatchers -------------------------------------------------------------------

class GoferDispatcher(object):

    def init_cds(self, cds):
        '''
        Contacts the CDS and requests that it do any initialization tasks it needs to.

        This method runs synchronously and will not return until after the CDS has responded
        or an error occurs.

        @param cds: A cds to be initialized.
        @type cds: CDS model object.

        @return: The CDS shared secret.
        @rtype: str
        '''
        secret = self._send(self._cds_stub(cds).initialize)
        return secret

    def release_cds(self, cds):
        '''
        Contacts the CDS and requests that it do any releasing tasks it needs to.

        This method runs synchronously and will not return until after the CDS has responded
        or an error occurs.

        @param cds: A cds to be released.
        @type cds: CDS model object.
        '''
        self._send(self._cds_stub(cds).release)

    def sync(self, cds, repos):
        '''
        Requests the CDS perform a sync with the pulp server. The current list of repos
        assigned to the CDS is sent as part of this call. It is up to the CDS to determine
        if a previously synchronized repo no longer exists in this set and delete its copy
        of the repo.

        This method runs synchronously and will not return until after the CDS has responded
        or an error occurs.

        @param cds: A cds to be synced.
        @type cds: CDS model object.

        @param repos: A list of repos to be synced.
        @type repos: list
        '''
        server_url = constants.SERVER_SCHEME + config.config.get('server', 'server_name')
        repo_relative_url = config.config.get('server', 'relative_url')
        repo_base_url = '%s/%s' % (server_url, repo_relative_url)
        timeout = self.__timeout('sync_timeout')
        log.info('sync using timeout=%s', timeout)
        stub = self._cds_stub(cds, timeout)

        self._send(stub.sync, repo_base_url, repos)

    def set_global_repo_auth(self, cds, cert_bundle):
        '''
        Sends the global repo authentication credentials to a specific CDS. If the
        bundle is None, the effect is that global repo authentication is disabled.

        @param cds: CDS to send the message to
        @type  cds:  L{CDS}

        @param cert_bundle: cert bundle to send to the CDS; may be None
        @type  cert_bundle:  see pulp.repo_auth.repo_cert_utils
        '''
        self._send(self._cds_stub(cds).set_global_repo_auth, cert_bundle)

    def set_repo_auth(self, cds, repo_id, repo_relative_path, cert_bundle):
        '''
        Sends repo authentication credentials to a specific CDS. If the bundle is
        None, the effect is that repo authentication is disabled for that repo.

        @param cds: CDS to send the message to
        @type  cds: L{CDS}

        @param repo_id: identifies the repo being configured
        @type  repo_id: str

        @param repo_relative_path: used to match a request as being against this repo
        @type  repo_relative_path: str

        @param cert_bundle: cert bundle to send to the CDS; may be None
        @type  cert_bundle:  see pulp.repo_auth.repo_cert_utils
        '''
        self._send(self._cds_stub(cds).set_repo_auth, repo_id, repo_relative_path, cert_bundle)

    def update_group_membership(self, cds, group_name, member_cds_hostnames):
        '''
        Sends a message to the given CDS describing a group update event. This
        will be sent both when a CDS first joins a group and for all subsequent
        changes to CDS membership in that group.

        @param cds: CDS to send the message to
        @type  cds: L{CDS}

        @param group_name: ID of the group the CDS belongs to
        @type  group_name: str

        @param member_cds_hostnames: list of hostnames of all CDS instances in the group
                                     (this will include the CDS being sent the message)
        @type  member_cds_hostnames: list of str
        '''
        self._send(self._cds_stub(cds).update_group_membership, group_name, member_cds_hostnames)
        
    def _send(self, func, *args):
        '''
        Utility function to execute a remote CDS operation, translating Gofer
        exceptions to Pulp ones.

        @param func: function to execute
        @type  func: function

        @param args: any arguments to pass to the function
        @type  args: any
        '''
        try:
            result = func(*args)
            return result
        except RequestTimeout, e:
            raise CdsTimeoutException(e), None, sys.exc_info()[2]
        except NotAuthorized, e:
            raise CdsAuthException(e), None, sys.exc_info()[2]
        except DispatchError, e:
            raise CdsCommunicationsException(e), None, sys.exc_info()[2]
        except Exception, e:
            # This is likely the case that the error originated in the CDS plugin itself
            raise CdsMethodException(e), None, sys.exc_info()[2]

    def _cds_stub(self, cds, timeout=None):
        '''
        Instantiates a stub to the CDS. Invocations on the CDS may be done through
        the stub.

        @param cds: domain entity for the CDS; may not be None
        @type  cds: L{CDS} instance

        @param timeout: The messaging timeout (initial, duration)
        @type timeout: tuple

        @return: gofer stub
        @rtype:  object with the same methods as the CDS plugin
        '''
        agent = CdsAgent(cds)
        stub = agent.cdsplugin(timeout=timeout)
        return stub

    def __timeout(self, property):
        '''
        Get a messaging timeout property.
        Property value can be single integer or two integers separated
        by a comma(,).  When a single integer is specified, it is applied
        to the duration and the initial is defaulted to (10).
        @param property: A messaging I{timeout} property name.
        @type property: str
        @return: A gofer timout tuple (initial, duration)
        @rtype: tuple
        '''
        pval = config.config.get('cds', property)
        if pval:
            parts = pval.split(':', 1)
            if len(parts) > 1:
                return int(parts[0]), int(parts[1])
            else:
                return 10, int(parts[0])
        else:
            return None
