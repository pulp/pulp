import argparse
import pkg_resources
import pyparsing as pp
import sys

from pulp.plugins.loader import manager
from pulp.server.db.connection import initialize as db_initialize
from pulp.server.db.model import FileContentUnit

from pulp_integrity.validator import Validation


class ValidationFactoryMixin(object):
    """Common interface for a validation CLI argument parser that works as a validation factory."""
    validator_types = {}
    validators = {}

    @classmethod
    def validator_factory(cls, validator_name):
        """Instantiate a validator from the validator types accumulated by the CLI args parsing.

        :param validator_name: name of the validator to instantiate
        :type validator_name: basestring
        :returns: a pulp_integrity.validation.Validator instance
        """
        if validator_name not in cls.validator_types:
            raise argparse.ArgumentTypeError('Unknown validator: %(v)s' % {
                'v': validator_name,
            })
        validator = cls.validators[validator_name] = cls.validator_types[validator_name]()
        validator.entrypoint_id = cls.validator_types[validator_name].entrypoint_id
        return validator

    @classmethod
    def load(cls):
        """Load validator types found in pkg_resources entry points.

        This method also tags the validator type entry point with an identifier used
        later on to relate the validator to its results.

        :returns: None
        """
        for entry in pkg_resources.iter_entry_points('validators'):
            validator_type = cls.validator_types[entry.name] = entry.load()
            validator_type.entrypoint_id = "{}, {}, {}:{}".format(
                entry.name, entry.dist, entry.module_name, validator_type.__name__)

    @classmethod
    def setup_validators(cls, parsed_args):
        """Set up each loaded validator instance.

        A stateful validator delayed setup; propagates the parsed_args to
        every instantiated validator setup method.

        :param parsed_args: CLI args passed down to setup the validators
        :type parsed_args: argparse.Namespace
        :reutrns: None
        """
        for validator_name in cls.validators:
            validator = cls.validators[validator_name]
            validator.setup(parsed_args)


class ChainingValidationFactory(argparse.Action, ValidationFactoryMixin):
    """A CLI action chaining validators into a [[[v1], v2], v3]-like validation.

    A silly parser that always nests validators into separate validations
    in order to quit early.
    """
    validation_struct = []

    @classmethod
    def include_validator(cls, validator):
        """Nest current validation into a new one, adding the validator provided.

        Builds the future validation object as a class-level attribute,
        a scaffolding of nested lists and validator instances.

        :param validator: the validator to nest into the current validation scaffolding level
        :type validator: pulp_integrity.validation.Validator
        :returns: None
        """
        cls.validation_struct = [cls.validation_struct, validator]

    @classmethod
    def register(cls, parser):
        """Register this class as an action for the validation construction with the arg parser.

        :param parser: the CLI argparse parser
        :type parser: argparse.ArgumentParser
        """
        parser.add_argument('--check', action=cls, choices=cls.validator_types, nargs='+',
                            help='Check units with specified validators')

    def __call__(self, parser, namespace, values, option_string):
        """The argparse Action interface; the factory of the validation.

        Processes all the '--check' CLI argument values, creating a validation structure.

        :param parser: argparse CLI parser object
        :type parser: argparse.ArgumentParser
        :param namespace: the CLI argument values namespace being built
        :type namespace: argparse.Namespace
        :param values: the current CLI '--check' value(s) being processed
        :type values: a list of basestrings
        :param option_string: ignored
        :returns: None
        """
        for validator_name in values:
            self.include_validator(self.validator_factory(validator_name))
            setattr(namespace, 'validation_struct', self.validation_struct)


class ParsingValidationFactory(argparse.Action, ValidationFactoryMixin):
    """A custom expression, CLI parsing-based validation factory.

    Processes the '--validation' CLI argument value creating a validation structure
    matching the structure provided on the CLI:

          ((v1 v2) v3) -> [[v1, v2], v3]

    Parent validations are skipped if child validations fail,
    sibling validations are always processed.

    The parser/grammar is from:
    https://stackoverflow.com/questions/18953433/issue-in-parsing-lisp-input-to-python
    """
    # Parser grammar definigion
    validator_expr = pp.Word(
        pp.alphas + '_', pp.alphanums + '_'
    ).setParseAction(lambda s, l, t: [ValidationFactoryMixin.validator_factory(t[0])])
    validation_expr = pp.Forward()
    validation_expr << pp.nestedExpr(content=pp.OneOrMore(validator_expr | validation_expr))
    validation_expr = pp.OneOrMore(validation_expr)

    @classmethod
    def register(cls, parser):
        """Register this class as an action for the validation construction with the arg parser.

        :param parser: the CLI argparse parser
        :type parser: argparse.ArgumentParser
        """
        parser.add_argument(
            '--validation', action=cls,
            help="""
            Specify a validation expression as nested lists:
                ((dark_content existence) size)

            - nesting the validators, parent validators are skipped on child validation failures
            - validators on the same level are executed no matter same-level validation failures
            """,
        )

    def __call__(self, parser, namespace, values, option_string):
        """The argparse Action interface; the factory of the validation.

        :param parser: argparse CLI parser object
        :type parser: argparse.ArgumentParser
        :param namespace: the CLI argument values namespace being built
        :type namespace: argparse.Namespace
        :param values: the current CLI '--check' value(s) being processed
        :type values: basestring
        :param option_string: ignored
        :returns: None
        """
        try:
            setattr(namespace, 'validation_struct',
                    self.validation_expr.parseString(values).asList())
        except pp.ParseException as exc:
            raise argparse.ArgumentError(self, exc)


class ModelsFactory(argparse.Action):
    """Argparse action to collect all file content unit models the user wishes to check."""
    model_types = {}
    models = {}

    @classmethod
    def add_model(cls, model_name, model):
        """Register the content model with this class.

        Only FileContentUnit subtypes are considered.

        :param model_name: name of the model to use; entrypoint
        :type model_name: basestring
        :param model: the pulp DB model instance
        :type model: pulp.server.db.model.FileContentUnit
        :returns: None
        """
        if not issubclass(model, FileContentUnit):
            return

        cls.model_types[model_name] = model

    @classmethod
    def load(cls):
        """Load all possible Pulp content models and register them as the CLI --model choices.

        :returns: None
        """
        pm = manager.PluginManager()
        for model_name in pm.unit_models:
            cls.add_model(model_name, pm.unit_models[model_name])

    @classmethod
    def register(cls, parser):
        """Register this class as an action for the content unit models parsing.

        :param parser: the CLI argparse parser
        :type parser: argparse.ArgumentParser
        """
        parser.add_argument('--model', action=cls, choices=cls.model_types, nargs='*',
                            dest='models', help='Limit the checks to specified unit models',
                            default=cls.model_types)

    def __call__(self, parser, namespace, model_names, option_string):
        """The argparse Action interface; the factory of the content unit models.

        Registers the content unit models in the namespace.models attribute.

        :param parser: argparse CLI parser object
        :type parser: argparse.ArgumentParser
        :param namespace: the CLI argument values namespace being built
        :type namespace: argparse.Namespace
        :param model_names: the current CLI '--model' values being processed
        :type values: a list of basestrings
        :param option_string: ignored
        :returns: None
        """

        attr = self.models
        for model_name in model_names:
            try:
                attr[model_name] = self.model_types[model_name]
            except KeyError:
                raise argparse.ArgumentTypeError('Oops, %(m)s model was not loaded!' % {
                    'm': model_name,
                })
        setattr(namespace, self.dest, attr)


def print_validator_field_value(field, value):
    """Custom validator (JSON) field printer.

    The entrypoint validator tag/id is printed rather than the repr(validator).

    :param field: the filed name
    :type field: basestring
    :param value: the validator object to print
    :type value: pulp_integrity.validation.Validator
    :returns: None
    """
    print '    "{}": "{}"'.format(field, value.entrypoint_id),


def print_unit_field(field, value):
    """Custom unit (JSON) field printer.

    Both the repr(unit) and unit.id are printed.

    :param field: the filed name
    :type field: basestring
    :param value: the unit object to print
    :type value: pulp.server.db.model.FileContentUnit
    :returns: None
    """
    print '    "{}": "{}" ,'.format(field, value)
    print '    "unit_id": "{}"'.format(value.id),


def print_repo_field_value(field, value):
    """Custom repo (JSON) field printer.

    The repo_id is printed.

    :param field: the filed name; ignored: repo_id is used instead
    :type field: basestring
    :param value: the repo_id to print
    :type value: basestring; repo_id
    :returns: None
    """
    print '    "repo_id": "{}"'.format(value),


def print_default_field(field, value):
    """A default (JSON) field printer.

    The repr(value) is printed.

    :param field: the filed name
    :type field: basestring
    :param value: the object to print
    :type value: type
    :returns: None
    """
    print '    "{}": "{}"'.format(field, value),


PRINT_FIELD_MAPPING = {
    'unit': print_unit_field,
    'validator': print_validator_field_value,
    'repository': print_repo_field_value,
}


def print_result(result, first):
    """Print a single validation result record.

    Handles first--last item separation with the ',' printing.

    :param result: the validation result to print
    :type result: an instance of collections.namedtuple; the result type
    :param first: the first flag; is this the first record to print?
    :type first: True/False
    """
    # handle list items separator (,)
    if not first:
        print ','

    print '  {'
    first = True
    for field in result._fields:
        if not first:
            print ','
        value = getattr(result, field)
        PRINT_FIELD_MAPPING.get(field, print_default_field)(field, value)
        first = False
    print '\n  }',


def main():
    exit_code = 0

    db_initialize('pulp_database')

    argparser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    options_parser = argparser.add_argument_group('options')
    validation_parser = argparser.add_mutually_exclusive_group()

    ModelsFactory.load()
    ModelsFactory.register(options_parser)
    ChainingValidationFactory.load()
    ChainingValidationFactory.register(validation_parser)
    ParsingValidationFactory.load()
    ParsingValidationFactory.register(validation_parser)

    try:
        args = argparser.parse_args()
    except Exception as err:
        print >> sys.stderr, err
        return 2
    if not hasattr(args, 'validation_struct'):
        argparser.error('No checks specified')

    ValidationFactoryMixin.setup_validators(args)

    # Custom JSON results printing to avoid having to accumulate the results just to dump
    # them at the end of the day; the possible results size is couple of repos worth of
    # units so 10k records easily
    # Print the JSON header
    first = True
    print '{'
    print '  "report": ['

    # get report for all supported units
    for modelname in args.models:
        for unit in args.models[modelname].objects:
            validation = Validation.from_iterable(args.validation_struct)
            validation(unit)
            for result in validation.results:
                if not bool(result):
                    exit_code = 1
                    print_result(result, first)
                    first = False

    # get any accumulated results
    for validator_name in ValidationFactoryMixin.validators:
        validator = ValidationFactoryMixin.validators[validator_name]
        for result in validator.results:
            if not bool(result):
                exit_code = 1
                print_result(result, first)
                first = False

    # JSON footer
    print '\n  ]'
    print '}'

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
