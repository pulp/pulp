from gettext import gettext as _
import logging
import os

_LOG = logging.getLogger(__name__)


class NonEmptyValidation(object):
    """
    Validates that the value is not None
    """
    def __call__(self, value, config):
        """
        :param value: value to validate
        :type value: any
        :param config: distributor config
        :type config: PulpCallConfig object

        :return: tuple indicating whether config value validates and error message or None
        :rtype: (bool, str) or (bool, None)
        """
        if value:
            return (True, None)
        else:
            return (False, self._err(value))

    def _err(self, value):
        """
        :param value: value that did not pass validation
        :type value: any

        :return: error message
        :rtype: str
        """
        return _("attribute cannot be empty")


class TypeValidation(object):
    """
    Validates that the value is one of allowed types
    """
    def __init__(self, allowed_types):
        """
        :param allowed_types: list of valid types
        :type allowed_types: list of types
        """
        self.allowed_types = allowed_types

    def __call__(self, value, config):
        """
        :param value: value to validate
        :type value: any
        :param config: distributor config
        :type config: PulpCallConfig object

        :return: tuple indicating whether config value validates and error message or None
        :rtype: (bool, str) or (bool, None)
        """
        if all(issubclass(type(value), _type) for _type in self.allowed_types):
            return (True, None)
        else:
            return (False, self._err(value))

    def _err(self, value):
        """
        :param value: value that did not pass validation
        :type value: any

        :return: error message
        :rtype: str
        """
        params = {'type': type(value), 'allowed_types': ", ".join(self.allowed_types)}
        return _("%(type)s type is not one of allowed types: %(allowed_types)s") % params


class RelativePathValidation(object):
    """
    Validates that a path does not start with a forward slash.
    """
    def __call__(self, value, *args):
        """
        :param value: path to validate
        :param args: any extra args that get passed in but are not needed for validation

        :return: tuple indicating whether config value validates and error message or None
        :rtype: (bool, str) or (bool, None)
        """
        if os.path.isabs(value):
            return (False, self._err(value))
        else:
            return (True, None)

    def _err(self, value):
        """
        :param value: value that did not pass validation
        :type value: any

        :return: error message
        :rtype: str
        """
        return _("attribute cannot start with a /")


REMOTE_MANDATORY_KEYS = {
    "ssh_identity_file": [TypeValidation([basestring]), NonEmptyValidation()],
    "ssh_user": [TypeValidation([basestring]), NonEmptyValidation()],
    "host": [TypeValidation([basestring]), NonEmptyValidation()],
    "root": [TypeValidation([basestring]), NonEmptyValidation()]
}

REMOTE_OPTIONAL_KEYS = {
    "remote_units_path": [TypeValidation([basestring]), RelativePathValidation()]
}


def validate_config(repo, config, config_conduit):
    """
    Validate the prospective configuration instance for the given repository.

    :param repo: repository to validate the config for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance to validate
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param config_conduit: conduit providing access to relevant Pulp functionality
    :type  config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit

    :return: tuple of (bool, str) stating that the configuration is valid or not and why
    :rtype:  tuple of (bool, str) or (bool, None)
    """
    _config = config.flatten()  # now config is {}
    err_list = []

    if "rsync_extra_args" in _config:
        (valid, err) = TypeValidation([list])(_config["rsync_extra_args"], _config)
        if not valid:
            err_list.append("rsync_extra_args: %s" % err)

    if "remote" not in _config or ("remote" in _config and not isinstance(_config["remote"], dict)):
        err_list.append("'remote' dict missing in distributor's configuration")
    else:
        missing_attr_tmpl = _("'%(attribute)s' is missing in 'remote' section of distributor's '"
                              "configuration")
        for attr, validations in REMOTE_MANDATORY_KEYS.iteritems():
            if attr not in _config["remote"]:
                err_list.append(missing_attr_tmpl % {'attribute': attr})
                continue
            for validation in validations:
                succeed, _err = validation(_config["remote"][attr], _config)
                if not succeed:
                    err_list.append(_("%(attribute)s : %(error)s") % {'attribute': attr,
                                                                      'error': _err})
        for attr, validations in REMOTE_OPTIONAL_KEYS.iteritems():
            if attr not in _config["remote"]:
                continue
            for validation in validations:
                succeed, _err = validation(_config["remote"][attr], _config)
                if not succeed:
                    err_list.append(_("%(attribute)s : %(error)s") % {'attribute': attr,
                                                                      'error': _err})
    if err_list:
        return (False, "\n".join(err_list))
    else:
        return (True, None)
