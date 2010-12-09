#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

'''
Contains classes that are used to send messages to CDS instances.
'''

# Python
import logging

# 3rd Party
from gofer.messaging.dispatcher import DispatchError
from gofer.messaging.policy import RequestTimeout
from gofer.proxy import Agent


log = logging.getLogger(__name__)


# -- exceptions -------------------------------------------------------------------

class CdsDispatcherException(Exception):
    '''
    Base class for all dispatcher-related exceptions.
    '''
    def __init__(self, wrapped_exception):
        self.wrapped_exception = wrapped_exception

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
        '''

        # Gofer doesn't have a good way of differentiating between issues contacting
        # the CDS and exceptions coming from the CDS itself, so the following long try
        # block differentiates and throws the appropriate dispatcher exception.

        try:
            self._cds_stub(cds).initialize()
        except RequestTimeout, e:
            raise CdsTimeoutException(e)
        except DispatchError, e:
            raise CdsCommunicationsException(e)
        except Exception, e:
            raise CdsMethodException(e)

    def sync(self, cds, repos):
        '''
        Requests the CDS perform a sync with the pulp server. The current list of repos
        assigned to the CDS is sent as part of this call. It is up to the CDS to determine
        if a previously synchronized repo no longer exists in this set and delete its copy
        of the repo.

        This method runs synchronously and will not return until after the CDS has responded
        or an error occurs.
        '''

        # Gofer doesn't have a good way of differentiating between issues contacting
        # the CDS and exceptions coming from the CDS itself, so the following long try
        # block differentiates and throws the appropriate dispatcher exception.

        try:
            self._cds_stub(cds).sync(repos)
        except RequestTimeout, e:
            raise CdsTimeoutException(e)
        except DispatchError, e:
            raise CdsCommunicationsException(e)
        except Exception, e:
            raise CdsMethodException(e)


    def _cds_stub(self, cds):
        '''
        Instantiates a stub to the CDS. Invocations on the CDS may be done through
        the stub.

        @param cds: domain entity for the CDS; may not be None
        @type  cds: L{CDS} instance

        @return: gofer stub
        @rtype:  object with the same methods as the CDS plugin
        '''
        agent = Agent(self._cds_uuid(cds))
        stub = agent.CdsGoferReceiver()
        return stub

    def _cds_uuid(self, cds):
        '''
        Generates the UUID for the message queue that the CDS will be listening on. The
        algorithm used by this method should match what it used on the CDS so that it
        will be listening on the correct queue.

        @param cds: domain entity for the CDS; may not be None
        @type  cds: L{CDS} instance

        @return: uuid suitable to pass to the message bus when sending messages to this CDS
        @rtype:  string
        '''
        # return 'cds-' + cds['hostname']
        return cds['hostname']