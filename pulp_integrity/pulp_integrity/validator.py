from collections import namedtuple
import functools
import itertools

import pulp.server.db.model as model


class ValidationError(Exception):
    """A generic validation error."""


# repository can be None
ValidationFailure = namedtuple('ValidationFailure', ('validator', 'unit', 'repository', 'error'))
# this is False in the bool context
ValidationFailure.__nonzero__ = staticmethod(lambda: False)
ValidationNotApplicable = namedtuple('ValidationNotApplicable', ('validator', 'unit'))
ValidationSuccess = namedtuple('ValidationSuccess', ('validator', 'unit'))
# separate failure type; no repository and path instead of unit
# because dark content is defined by storage path without a unit
DarkPath = namedtuple('DarkPath', ('validator', 'path', 'error'))
DarkPath.__nonzero__ = staticmethod(lambda: False)


class Validator(object):
    def __call__(self, unit, validation):
        """Perform a sanitized validation.

        Appends a result to validation.results.

        :param unit: a content unit to validate
        :type unit: pulp.server.db.model.FileContentUnit
        :returns: None
        """
        if not self.applicable(unit):
            validation.results.append(ValidationNotApplicable(self, unit))

        try:
            self.validate(unit, validation)
        except ValidationError as exc:
            repository = getattr(exc, 'repository', None)
            validation.results.append(ValidationFailure(self, unit, repository, exc))
        else:
            validation.results.append(ValidationSuccess(self, unit))

    def applicable(self, unit):
        """Check if this validator is applicable to the unit.

        :param unit: the unit being checked
        :type unit: pulp.server.db.model.FileContentUnit
        :return: True/False
        """
        return isinstance(unit, model.FileContentUnit)

    def validate(self, unit, validation):
        """Check the unit in the context of the ongoing validation.

        :param unit: the unit to be checked
        :type unit: pulp.server.db.model.FileContentUnit
        :returns: None
        :raises: ValidationError in case validation didn't pass as expected
        """
        pass

    @property
    def results(self):
        """Iterate over the accumulated results of this validator.

        :return: iterator over the accumulated results
        """
        # a default, empty iterator
        return
        yield

    def setup(self, parsed_args):
        """Set up the validator state according to the parsed arguments.

        :param parsed_args: all parsed CLI arguments
        :type parsed_args: argparse.Namespace
        :returns: None
        """
        pass


class MultiValidator(Validator):
    def __call__(self, unit, validation):
        """Perform a sanitized validation.

        Extends the valiation.results with calculated results.

        :param unit: a content unit to validate
        :type unit: pulp.server.db.model.FileContentUnit
        :returns: None
        """
        if not self.applicable(unit):
            validation.results.append(ValidationNotApplicable(self, unit))
            return

        for result in self.validate(unit, validation):
            validation.results.append(result)

    @staticmethod
    def affects_repositories(failure_factory=ValidationFailure):
        """Declare a validator.validate method affecting all the unit repositories.

        :param failure_factory: a (custom) ValidationFailure factory
        :type failure_factory: callable(validator, unit, repo_id, ValidationError)
        """
        def outer(func):
            @functools.wraps(func)
            def inner(self, unit, validation, *args, **kwargs):
                try:
                    func(self, unit, validation, *args, **kwargs)
                except ValidationError as exc:
                    for repo_id in validation.repo_ids(unit):
                        yield failure_factory(self, unit, repo_id, exc)
                else:
                    yield ValidationSuccess(self, unit)
                finally:
                    raise StopIteration()
            return inner
        return outer


class Validation(object):
    """Chain&nest validators."""
    def __init__(self, children=None, validators=None, invariant=None):
        self.children = children or []
        self.validators = validators or []
        self._visited = False
        # all the children share a common, flat results list eventually
        # the order of results is given by the order of the children walk
        self.results = None
        self.invariant = invariant or self.almost_all_invariant
        self._repo_ids = None

    @staticmethod
    def almost_all_invariant(iterable, start):
        """Check that last couple of iterable items are bool(item) -> True.

        Assuming all previously seen items were bool(item) -> True, this avoids
        repeated validation results checks to be O(len(iterable)**2) complexity by
        examining only the recently appended results.

        :param iterable: the iterable to examine (contains validation results)
        :type iterable: iterable
        :param start: where to start the check from
        :type start: int(for an itertools.islice construction)
        """
        return all(itertools.islice(iterable, start, len(iterable)))

    @classmethod
    def from_iterable(cls, iterable):
        """Construct a validation object from (nested) Validator iterables.

        :param cls: the valiation type to construct
        :type cls: type
        :param iterable: a (nested) iterable containing Validator objects
        :type iterable: a (nested) iterable over Validator objects
        :returns: an instance of cls
        """
        validators = []
        children = []
        for item in iterable:
            try:
                # add a child validation
                children.append(cls.from_iterable(item))
            except TypeError:
                # add a leaf (validator)
                validators.append(item)
        return cls(validators=validators, children=children)

    def repo_ids(self, unit):
        """Get related unit repo ids.

        Assumes each validation instance is run against at most one unit.
        Lazy.

        :return: a list of repo ids
        """
        # NOTE: the benefits are limited by the nesting; ids won't be shared across
        # the nested validations even though the same unit is but this may be OK as
        # only validators on the same "level" are executed in case of a failure.
        if self._repo_ids is not None:
            return self._repo_ids

        self._repo_ids = [
            repo.repo_id for repo in model.RepositoryContentUnit.objects(
                unit_id=unit.id).only('repo_id')
        ]
        return self._repo_ids

    def __iter__(self):
        # A DFS children iteration
        if self._visited:
            raise StopIteration('Already visited')
        self._visited = True

        for child in self.children:
                yield child

    def __call__(self, unit, results=None):
        """Apply the (nested validation) validators to the unit.

        Nested valiation failures terminate parent validation.
        Sibling validation failures are tolerated.
        Validator unit results are appended to the results parameter.

        :param unit: the unit to validate
        :type unit: pulp.server.db.model.FileContentUnit
        :param result: the results list being build during the validation
        :type result: a list of validation results
        :returns: None
        """
        if results is None:
            results = []

        self.results = results
        for validation in self:
            old_len = len(results)
            validation(unit, results)
            # fast forward in case of nested errors
            if not self.invariant(self.results, old_len):
                return

        for validator in self.validators:
            validator(unit, self)
