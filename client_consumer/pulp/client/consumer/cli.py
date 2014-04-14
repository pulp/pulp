# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import urllib2
import errno

from gettext import gettext as _

from M2Crypto import RSA
from M2Crypto.util import no_passphrase_callback
from M2Crypto.X509 import X509Error

from pulp.bindings.exceptions import NotFoundException
from pulp.client.arg_utils import args_to_notes_dict
from pulp.client.consumer_utils import load_consumer_id
from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag
from pulp.client.extensions import exceptions
from pulp.client import validators


OPTION_EXCHANGE_KEYS = PulpCliFlag('--keys', _('exchange public keys with the server'))


# -- framework hook -----------------------------------------------------------

@priority()
def initialize(context):

    # Common Options
    d = 'uniquely identifies the consumer; only alphanumeric, ., -, and _ allowed'
    id_option = PulpCliOption('--consumer-id', _(d), required=True, validate_func=validators.id_validator_allow_dots)

    d = 'user-readable display name for the consumer'
    name_option = PulpCliOption('--display-name', _(d), required=False)

    d = 'user-readable description for the consumer'
    description_option = PulpCliOption('--description', _(d), required=False)

    d = 'adds/updates/deletes key-value pairs to pragmatically identify the repository; '
    d += 'pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
    d += 'be %(i)s by specifying this option multiple times; notes are deleted by '
    d += 'specifying "" as the value'
    d = _(d)

    update_note_d = d % {'i' : _('changed')}
    add_note_d =  d % {'i' : _('added')}

    update_note_option = PulpCliOption('--note', update_note_d, required=False, allow_multiple=True)
    add_note_option = PulpCliOption('--note', add_note_d, required=False, allow_multiple=True)

    # Register Command
    d = 'registers this consumer to the Pulp server'
    register_command = RegisterCommand(context, 'register', _(d))
    register_command.add_option(id_option)
    register_command.add_option(name_option)
    register_command.add_option(description_option)
    register_command.add_option(add_note_option)
    context.cli.add_command(register_command)

    # Update Command
    d = 'changes metadata of this consumer'
    update_command = UpdateCommand(context, 'update', _(d))
    update_command.add_option(name_option)
    update_command.add_option(description_option)
    update_command.add_option(update_note_option)
    update_command.add_option(OPTION_EXCHANGE_KEYS)
    context.cli.add_command(update_command)

    # Unregister Command
    d = 'unregisters this consumer from the Pulp server'
    unregister_command = UnregisterCommand(context, 'unregister', _(d))
    context.cli.add_command(unregister_command)

    # History Retrieval Command
    d = 'lists history of this consumer'
    context.cli.add_command(HistoryCommand(context, 'history', _(d)))

    d = 'displays the registration status of this consumer'
    context.cli.add_command(StatusCommand(context, 'status', _(d)))


def download(url, location):
    """
    Download files to the specified location.
    :param url: The file URL.
    :type url: str
    :param location: The absolute path to where the downloaded
        file is to be stored.
    :type location: str
    """
    request = urllib2.urlopen(url)
    try:
        content = request.read()
        fp = open(location, 'w+')
        try:
            fp.write(content)
        finally:
            fp.close()
    finally:
        request.close()


def update_server_key(conf):
    """
    Download the server's RSA key and store in the location
    specified in the configuration.
    :param conf: The consumer configuration object.
    :type conf: dict
    """
    host = conf['server']['host']
    location = conf['server']['rsa_pub']
    url = 'https://%s/pulp/static/rsa_pub.key' % host
    try:
        os.makedirs(os.path.dirname(location))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    download(url, location)


# -- common exceptions --------------------------------------------------------


class RegisterCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.register)
        self.context = context
        self.prompt = context.prompt

    def register(self, **kwargs):
        consumer_id = kwargs['consumer-id']

        # Check if this consumer is already registered

        existing_consumer = load_consumer_id(self.context)
        if existing_consumer:
            m = _('This system has already been registered as a consumer. Please '
                  'use the unregister command to remove the consumer before attempting '
                  'to re-register.')
            self.prompt.render_failure_message(m)
            return

        # Get other consumer parameters

        name = kwargs.get('display-name', consumer_id)
        description = kwargs.get('description')
        notes = kwargs.get('note')
        if notes:
            notes = args_to_notes_dict(notes, include_none=False)

        # Check write permissions to cert directory
        id_cert_dir = self.context.config['filesystem']['id_cert_dir']
        if not os.access(id_cert_dir, os.W_OK):
            msg = _("Write permission is required for %(d)s to perform this operation.")
            self.prompt.render_failure_message(msg % {'d': id_cert_dir})
            return exceptions.CODE_PERMISSIONS_EXCEPTION

        # RSA key
        path = self.context.config['authentication']['rsa_key']
        key = RSA.gen_key(2048, 65535, no_passphrase_callback)
        key.save_key(path, None)
        path = self.context.config['authentication']['rsa_pub']
        key.save_pub_key(path)
        fp = open(path)
        try:
            rsa_pub = fp.read()
        finally:
            fp.close()

        # Call the server

        reply = self.context.server.consumer.register(
            consumer_id,
            name=name,
            description=description,
            notes=notes,
            rsa_pub=rsa_pub)

        certificate = reply.response_body['certificate']

        # Write consumer certificate

        id_cert_name = self.context.config['filesystem']['id_cert_filename']
        cert_filename = os.path.join(id_cert_dir, id_cert_name)
        fp = open(cert_filename, 'w')
        try:
            fp.write(certificate)
        finally:
            fp.close()

        # download server public key

        try:
            update_server_key(self.context.config)
        except Exception, e:
            msg = _('Download server RSA key failed [%(e)s]' % {'e': e})
            self.prompt.render_failure_message(msg)

        self.prompt.render_success_message('Consumer [%s] successfully registered' % consumer_id)


class UpdateCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.update)
        self.context = context
        self.prompt = context.prompt

    def update(self, **kwargs):
        consumer_id = load_consumer_id(self.context)
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return

        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        if 'note' in delta.keys():
            if delta['note']:
                delta['notes'] = args_to_notes_dict(kwargs['note'], include_none=False)
            delta.pop('note')
        # convert display-name to display_name
        key = 'display-name'
        if key in delta:
            v = delta.pop(key)
            key = key.replace('-', '_')
            delta[key] = v

        if kwargs.get(OPTION_EXCHANGE_KEYS.keyword):
            path = self.context.config['authentication']['rsa_pub']
            fp = open(path)
            try:
                delta['rsa_pub'] = fp.read()
            finally:
                fp.close()

        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.prompt.render_success_message('Consumer [%s] successfully updated' % consumer_id)
            if not kwargs.get(OPTION_EXCHANGE_KEYS.keyword):
                return
            try:
                update_server_key(self.context.config)
            except Exception, e:
                msg = _('Download server RSA key failed [%(e)s]' % {'e': e})
                self.prompt.render_failure_message(msg)
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')


class UnregisterCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.unregister)
        self.context = context
        self.prompt = context.prompt

        d = 'if specified, the local consumer identification certificate will be '\
            'removed even if the server cannot be contacted'
        self.create_flag('--force', _(d))

    def unregister(self, **kwargs):

        force = kwargs['force']

        # Check write permissions to cert directory
        id_cert_dir = self.context.config['filesystem']['id_cert_dir']
        if not os.access(id_cert_dir, os.W_OK):
            msg = _("Write permission is required for %(d)s to perform this operation.")
            self.prompt.render_failure_message(msg % {'d': id_cert_dir})
            return exceptions.CODE_PERMISSIONS_EXCEPTION

        # Get the consumer ID
        try:
            consumer_id = load_consumer_id(self.context)
            if not consumer_id:
                msg = _('This consumer is not registered to the Pulp server.')
                self.context.prompt.render_failure_message(msg)
                return exceptions.CODE_NOT_FOUND
        except X509Error:
            self.context.logger.exception('Consumer certificate not valid.')
            if force:
                self._delete_cert()
                msg = _('Consumer certificate deleted.')
                self.context.prompt.render_success_message(msg)
                self._forced_warning()
                return os.EX_OK
            else:
                msg = _('Consumer certificate not valid. Please retry using the --force option.')
                self.context.prompt.render_failure_message(msg)
                return os.EX_DATAERR

        # Unregister on the server
        forced = True
        try:
            self.context.server.consumer.unregister(consumer_id)
            forced = False
        except NotFoundException:
            if not force:
                msg = _('This consumer does not exist on the server. Please retry using the --force option.')
                self.prompt.render_failure_message(msg)
                return exceptions.CODE_NOT_FOUND
        except X509Error:
            self.context.logger.exception('SSL connection failed.')
            if not force:
                msg = _('SSL connection failed. This error may be ignored by using the --force option.')
                self.prompt.render_failure_message(msg)
                return os.EX_OSERR
        except Exception:
            self.context.logger.exception('Unregistration failed')
            if not force:
                msg = _('Unregistration failed on the server. This error may be ignored by using the --force option.')
                self.prompt.render_failure_message(msg)
                return exceptions.CODE_UNEXPECTED

        # Unregister locally
        self._delete_cert()
        msg = 'Consumer [%(c)s] successfully unregistered' % dict(c=consumer_id)
        self.context.prompt.render_success_message(msg)
        if forced:
            self._forced_warning()

    def _forced_warning(self):
        msg = _('Warning: The unregistration was not coordinated with the server.')
        self.context.prompt.render_warning_message(msg)

    def _delete_cert(self):
        id_cert_dir = self.context.config['filesystem']['id_cert_dir']
        id_cert_name = self.context.config['filesystem']['id_cert_filename']
        cert_filename = os.path.join(id_cert_dir, id_cert_name)
        if os.path.exists(cert_filename):
            os.remove(cert_filename)


class HistoryCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.history)
        self.context = context
        self.prompt = context.prompt

        d = 'limits displayed history entries to the given type;'
        d += 'supported types: ("consumer_registered", "consumer_unregistered", "repo_bound", "repo_unbound",'
        d += '"content_unit_installed", "content_unit_uninstalled", "unit_profile_changed", "added_to_group",'
        d += '"removed_from_group")'
        self.add_option(PulpCliOption('--event-type', _(d), required=False))
        self.add_option(PulpCliOption('--limit', 'limits displayed history entries to the given amount (must be greater than zero)', required=False))
        self.add_option(PulpCliOption('--sort', 'indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp', required=False))
        self.add_option(PulpCliOption('--start-date', 'only return entries that occur on or after the given date in iso8601 format (yyyy-mm-ddThh:mm:ssZ)', required=False))
        self.add_option(PulpCliOption('--end-date', 'only return entries that occur on or before the given date in iso8601 format (yyyy-mm-ddThh:mm:ssZ)', required=False))

    def history(self, **kwargs):
        consumer_id = load_consumer_id(self.context)
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return
        self.prompt.render_title(_('Consumer History [%(i)s]') % {'i' : consumer_id})

        history_list = self.context.server.consumer_history.history(consumer_id, kwargs['event-type'], kwargs['limit'], kwargs['sort'],
                                                            kwargs['start-date'], kwargs['end-date']).response_body
        filters = ['consumer_id', 'type', 'details', 'originator', 'timestamp']
        order = filters
        for history in history_list:
            self.prompt.render_document(history, filters=filters, order=order)


class StatusCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.status)
        self.context = context
        self.prompt = context.prompt

    def status(self):
        consumer_id = load_consumer_id(self.context)

        if consumer_id:
            server = self.context.config['server']['host']
            m = 'This consumer is registered to the server [%(s)s] with the ID [%(i)s].'
            self.prompt.render_success_message(_(m) % {'s': server, 'i' : consumer_id})
        else:
            m = 'This consumer is not currently registered.'
            self.prompt.render_paragraph(_(m))
