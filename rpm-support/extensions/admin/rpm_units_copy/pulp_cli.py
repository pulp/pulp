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

from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliCommand

# -- constants ----------------------------------------------------------------

TYPE_RPM = 'rpm'
TYPE_SRPM = 'srpm'
TYPE_DRPM = 'drpm'
TYPE_ERRATA = 'errata'

LOG = None # set by context

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    global LOG
    LOG = context.logger

    repo_section = context.cli.find_section('repo')
    copy_section = repo_section.create_subsection('copy', _('copy packages and errata between repositories'))

    rpm_usage_desc = 'Packages to copy from the source repository are determined by ' \
    'applying regular expressions for inclusion (match) and exclusion (not). ' \
    'Criteria are specified in the format "field=regex", for example "name=python.*". ' \
    'Except for the date checks, all arguments may be specified multiple times to further ' \
    'refine the matching criteria. ' \
    'Valid fields are: name, epoch, version, release, arch, buildhost, checksum, ' \
    'description, filename, license, and vendor.'
    rpm_usage_desc = _(rpm_usage_desc)

    copy_section.add_command(CopyCommand(context, 'rpm', _('copies RPMs from one repository into another'), rpm_usage_desc, TYPE_RPM))
    copy_section.add_command(CopyCommand(context, 'srpm', _('copies SRPMs from one repository into another'), rpm_usage_desc, TYPE_SRPM))
    copy_section.add_command(CopyCommand(context, 'drpm', _('copies DRPMs from one repository into another'), rpm_usage_desc, TYPE_DRPM))

# -- commands -----------------------------------------------------------------

class CopyCommand(PulpCliCommand):

    def __init__(self, context, name, description, usage_description, type_id):
        self.context = context
        self.type_id = type_id

        PulpCliCommand.__init__(self, name, description, self.copy, usage_description=usage_description)

        # General Options
        self.create_option('--from-repo-id', _('source repository from which units will be copied'), ['-f'], required=True)
        self.create_option('--to-repo-id', _('destination repository to copy units into'), ['-t'], required=True)
        self.create_flag('--dry-run', _('display the units that will be copied without performing the actual copy'), ['-d'])

        # Criteria Options
        m = 'field and expression to match when determining units for inclusion'
        self.create_option('--match', _(m), ['-m'], required=False, allow_multiple=True)

        m = 'field and expression to omit when determining units for inclusion'
        self.create_option('--not', _(m), ['-n'], required=False, allow_multiple=True)

        m = 'matches units whose value for the specified field is greater than the given value'
        self.create_option('--gt', _(m), required=False, allow_multiple=True)

        m = 'matches units whose value for the specified field is greater than or equal to the given value'
        self.create_option('--gte', _(m), required=False, allow_multiple=True)

        m = 'matches units whose value for the specified field is less than the given value'
        self.create_option('--lt', _(m), required=False, allow_multiple=True)

        m = 'matches units whose value for the specified field is less than or equal to the given value'
        self.create_option('--lte', _(m), required=False, allow_multiple=True)

        m = 'matches units added to the source repository on or after the given time; ' \
            'specified as a timestamp in iso8601 format'
        self.create_option('--after', _(m), ['-a'], required=False, allow_multiple=False)

        m = 'matches units added to the source repository on or before the given time; '\
            'specified as a timestamp in iso8601 format'
        self.create_option('--before', _(m), ['-b'], required=False, allow_multiple=False)

    def copy(self, **kwargs):
        from_repo = kwargs['from-repo-id']
        to_repo = kwargs['to-repo-id']

        try:
            criteria = args_to_criteria(self.type_id, kwargs)
        except InvalidCriteria, e:
            self.context.prompt.render_failure_message(_(e[0]))
            return

        if 'dry-run' in kwargs and kwargs['dry-run']:
            matching_units = self.context.server.repo_unit_search.search(from_repo, criteria).response_body
            matching_units_metadata = [u['metadata'] for u in matching_units]

            self.context.prompt.render_title(_('Matching Units'))
            self.context.prompt.render_document_list(matching_units_metadata, filters=['filename'], num_separator_spaces=0)
        else:

            # If rejected an exception will bubble up and be handled by middleware
            response = self.context.server.repo_unit_associations.copy_units(from_repo, to_repo, criteria)

            progress_msg = 'Progress on this task can be viewed using the '\
                           'commands under "repo tasks".'
            progress_msg = _(progress_msg)
            if response.response_body.is_postponed():
                d = 'Unit copy postponed due to another operation on the destination ' \
                    'repository. '
                d = _(d) + progress_msg
                self.context.prompt.render_paragraph(d)
                self.context.prompt.render_reasons(response.response_body.reasons)
            else:
                self.context.prompt.render_paragraph(progress_msg)

# -- utility ------------------------------------------------------------------

class InvalidCriteria(Exception):
    """
    Exception raised when the user specifies criteria options that cannot be
    converted into the necessary Pulp syntax. The argument passed in (e[0]) is
    the message that should be i18n'd and displayed to the user.
    """
    pass

def args_to_criteria(type_id, kwargs):
    """
    Translates relevant user entered arguments into the proper format to be
    submitted to the server as the unit copy criteria.

    @param kwargs: map of user entered options and values; may contain extra
                   options that this call does not care about
    @dict  kwargs: dict

    @return: value to be passed to the criteria argument on the unit copy call
    @rtype:  dict
    """

    # Simple part  :)
    criteria = {'type_ids' : [type_id]}

    # -- Unit Filters --

    unit_clauses = []

    # Look for each item in [0] of the tuple and if found, make mongo clauses
    # using [1] as the mongo keyword.
    unit_arg_to_mongo_map = [
        ('match', '$regex'),
        ('not', '$not'),
        ('gt', '$gt'),
        ('gte', '$gte'),
        ('lt', '$lt'),
        ('lte', '$lte'),
    ]

    for k, m in unit_arg_to_mongo_map:
        if k in kwargs and kwargs[k] is not None:
            clauses = _parse(kwargs[k], lambda x, y: {x : {m : y}})
            unit_clauses += clauses

    # Concatenate all of them into an $and clause
    if len(unit_clauses) > 0:
        if len(unit_clauses) > 1:
            unit_filters_clause = {'$and' : unit_clauses}
        else:
            unit_filters_clause = unit_clauses[0]
        filters = criteria.setdefault('filters', {})
        filters['unit'] = unit_filters_clause

    # -- Association Filters --

    association_clauses = []

    ass_arg_to_mongo_map = [
        ('after', '$gte'),
        ('before', '$lte'),
    ]

    for k, m in ass_arg_to_mongo_map:
        if k in kwargs and kwargs[k] is not None:
            clause = {'created' : {m : kwargs[k]}}
            association_clauses.append(clause)

    if len(association_clauses) > 0:
        if len(association_clauses) > 1:
            association_filters_clause = {'$and' : association_clauses}
        else:
            association_filters_clause = association_clauses[0]
        filters = criteria.setdefault('filters', {})
        filters['association'] = association_filters_clause

    return criteria

def _parse(args, mongo_func):
    """
    Parses a list of user supplied key value pairs and creates the appropriate
    mongo syntax based on the type of relationship being defined.

    The provided function must accept two parameters, the field name and value,
    and return the corresponding mongo clause that should be added to the
    criteria.

    If any of the arguments cannot correctly be parsed an exception is raised
    describing the issue.

    @param args: list of unparsed key/value pairs, expressed as "field=value"
    @type  args: list

    @param mongo_func: function to apply to the value
    @type  mongo_func: func

    @return: list of mongo syntax clauses to add to the criteria
    """

    # Consolidate multiple match calls with the same field into a single list
    clauses = []
    for user_opt in args:

        pieces = user_opt.split('=', 1)
        if len(pieces) != 2:
            raise InvalidCriteria('Criteria values must be specified in the format "field=value"')

        field = pieces[0]
        value = pieces[1]

        clause = mongo_func(field, value)
        clauses.append(clause)

    return clauses


