from gettext import gettext as _
import logging
import os

_LOG = logging.getLogger(__name__)


class OneOfValidation(object):
    """
    Validates that the the value is one of possible values
    """
    def __init__(self, values):
        """
        :param values: list of valid values
        """
        self.values = values

    def __call__(self, value, config):
        """
        :param value: value to validate
        :type value: any
        :param config: distributor config
        :type config: PulpCallConfig object

        :return: tuple indicating whether config value validates and error message or None
        :rtype: (bool, str) or (bool, None)
        """
        if value in self.values:
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
        params = {'value': value, 'allowed_values': ", ".join(self.values)}
        return _("%(value)s is not in allowed values: %(allowed_values)s") % params


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


class RequireOptionalIf(object):
    """
    Validates that if a particular config is present, other configs that are needed for it are also
    present.
    """
    def __init__(self, required_for_attr, condition):
        """
        :param required_for_attr: a list of required config keys or dictionary with keys in the
                                  config and values are lists of configs that need to be present
                                  in the value of the key in config.
        :type required_for_attr: list or dict
        :param condition: callable that takes a config name and returns a boolean
        :type condition: callable
        """
        self.required_for_attr = required_for_attr
        self.condition = condition

    def __call__(self, value, config):
        """
        :param value: config name that is being validated
        :type value: str
        :param config: configuration instance to validate
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :return: tuple indicating whether config value validates and error message or None
        :rtype: (bool, str) or (bool, None)
        """

        subconfig = config
        path = []
        if not self.condition(value):
            return (True, None)

        if isinstance(self.required_for_attr, list):
            fifo = [(x, subconfig, path) for x in self.required_for_attr]
        elif isinstance(self.required_for_attr, dict):
            fifo = [(val, subconfig.get(key), [key])
                    for key, val in self.required_for_attr.iteritems()]
        while fifo:
            (required_for_attr, subconfig, path) = fifo.pop(0)
            if isinstance(required_for_attr, list):
                for x in required_for_attr:
                    fifo.insert(0, (x, subconfig, path))
            elif isinstance(required_for_attr, dict):
                for key, val in required_for_attr.iteritems():
                    fifo.insert(0, (val, subconfig.get(key)), path + [key])
            elif isinstance(required_for_attr, basestring):
                if required_for_attr not in subconfig:
                    return (False, self._err(path + [required_for_attr]))
        return (True, None)

    def _err(self, path):
        """
        :param path: list of value that were missing
        :type path: list

        :return: error message
        :rtype: str
        """
        return _("%(attribute)s attribute is required") % {'attribute': "::".join(path)}


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
    "auth_type": [OneOfValidation(["publickey", "password"]),
                  RequireOptionalIf({"remote": ["ssh_password", "ssh_user"]},
                                    lambda x: x == "password"),
                  RequireOptionalIf({"remote": ["ssh_identity_file", "ssh_user"]},
                                    lambda x: x == "publickey")],
    "host": [TypeValidation([basestring]), NonEmptyValidation()],
    "root": [TypeValidation([basestring]), NonEmptyValidation()]
}

REMOTE_OPTIONAL_KEYS = {
    "remote_units_path": [TypeValidation([basestring]), RelativePathValidation()],
    "ssh_identity_file": [TypeValidation([basestring]), NonEmptyValidation()],
    "ssh_user": [TypeValidation([basestring]), NonEmptyValidation()],
    "ssh_password": [TypeValidation([basestring]), NonEmptyValidation()]
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
