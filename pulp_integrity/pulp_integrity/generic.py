import collections
import os
from os import path

from pulp.server import util
from pulp.plugins.util import verification

from pulp_integrity import validator


class MissingStoragePath(validator.ValidationError):
    """Missing storage path error."""


class InvalidStoragePathSize(validator.ValidationError):
    """Invalid storage path error."""


class InvalidStoragePathChecksum(validator.ValidationError):
    """Invalid storage path checksum."""


class DarkContentError(validator.ValidationError):
    """Dark content path error."""


MISSING_ERROR = MissingStoragePath('The path was not found on the filesystem.')
SIZE_ERROR = InvalidStoragePathSize('The path has an invalid size on the filesystem.')
CHECKSUM_ERROR = InvalidStoragePathChecksum('The path has an invalid checksum on the filesystem.')
DARK_CONTENT = DarkContentError('The path has no content unit in the database.')

UnitPathFailure = collections.namedtuple('UnitPathFailure',
                                         validator.ValidationFailure._fields + ('path',))
UnitPathFailure.__nonzero__ = staticmethod(lambda: False)


class DownloadedFileContentUnitValidator(validator.MultiValidator):
    def applicable(self, unit):
        """This validator is applicable to downloaded units only.

        :param unit: the unit being checked
        :type unit: pulp.server.db.model.FileContentUnit
        :returns: True/False
        """
        return (
            super(DownloadedFileContentUnitValidator, self).applicable(unit) and
            unit.downloaded
        )

    @staticmethod
    def failure_factory(validator, unit, repository, error):
        """This validator failure objects factory.

        :param validator: the validator that checked the units
        :type validator: pulp_integrity.validation.Validator
        :param: unit: the unit that failed the validation
        :type unit: pulp.server.db.model.FileContentUnit
        :param repository: repo_id to link this failure to
        :type repository: basestring
        :param error: the ValidationError that occurred during the validation
        :type error: a ValidationError object
        :returns: a UnitPathFailure object
        """
        return UnitPathFailure(validator, unit, repository, error, unit.storage_path)


class ExistenceValidator(DownloadedFileContentUnitValidator):
    """Check that the unit.storage_path exists on the disk."""

    @validator.MultiValidator.affects_repositories(
        failure_factory=DownloadedFileContentUnitValidator.failure_factory)
    def validate(self, unit, *args):
        """Check the unit.

        :param unit: the unit to check
        :type unit: pulp.server.db.model.FileContentUnit
        :param args: unused
        :returns: None
        :raises: MISSING_ERROR
        """
        if not path.exists(unit.storage_path):
            raise MISSING_ERROR


class SizeValidator(DownloadedFileContentUnitValidator):
    """Check that the unit.storage_path size matches the unit.size."""

    def applicable(self, unit):
        """Only units with the verify_size method are supported.

        :param unit: the unit to check the applicability of
        :type unit: pulp.server.db.model.FileContentUnit
        :retunrs: True/False
        """
        return (super(SizeValidator, self).applicable(unit) and
                hasattr(unit, 'verify_size'))

    @validator.MultiValidator.affects_repositories(
        failure_factory=DownloadedFileContentUnitValidator.failure_factory)
    def validate(self, unit, *args):
        """Check the unit.

        :param unit: the unit to check
        :type unit: pulp.server.db.model.FileContentUnit
        :param args: unused
        :returns: None
        :raises: MISSING_ERROR/SIZE_ERROR
        """
        try:
            unit.verify_size(unit.storage_path)
        except (IOError, OSError):
            raise MISSING_ERROR
        except verification.VerificationException:
            raise SIZE_ERROR


class ChecksumValidator(DownloadedFileContentUnitValidator):
    """Check that the unit.storage_path checksum matches the unit.checksum."""

    def applicable(self, unit):
        """Only units with the checksum and checksumtype attributes are supported.

        :param unit: the unit to check the applicability of
        :type unit: pulp.server.db.model.FileContentUnit
        :retunrs: True/False
        """
        return (super(ChecksumValidator, self).applicable(unit) and
                hasattr(unit, 'checksum') and hasattr(unit, 'checksumtype'))

    @validator.MultiValidator.affects_repositories(
        failure_factory=DownloadedFileContentUnitValidator.failure_factory)
    def validate(self, unit, *args):
        """Check the unit.

        :param unit: the unit to check
        :type unit: pulp.server.db.model.FileContentUnit
        :param args: unused
        :returns: None
        :raises: MISSING_ERROR/CHECKSUM_ERROR
        """
        try:
            with open(unit.storage_path, 'rb') as fd:
                checksums = util.calculate_checksums(fd, [unit.checksumtype])
        except (IOError, OSError):
            raise MISSING_ERROR
        if unit.checksum != checksums[unit.checksumtype]:
            raise CHECKSUM_ERROR


class DarkContentValidator(validator.MultiValidator):
    """Checks that every file under /var/lib/pulp/content/units relates to exactly one unit."""

    def applicable(self, unit):
        """This validator is applicable to downloaded units only.

        :param unit: the unit to check applicability of
        :type unit: pulp.server.db.model.FileContentUnit
        :returns: True/False
        """
        return (
            super(DarkContentValidator, self).applicable(unit) and
            unit.downloaded
        )

    def __init__(self):
        super(DarkContentValidator, self).__init__()
        self.paths = set()

    def setup(self, parsed_args):
        """Set this validator up.

        Walks the filesystem tree under /var/lib/pulp/content/units and collects all
        filenames found. Setting this up is might take considerable resources;
        couple of dozens of megabytes of RAM and IO-latency induced delay.
        An instance should be used as a singleton.

        :param parsed_args: parsed CLI arguments
        :type parsed_arg: argparse.Namespace
        :returns: None
        """
        self.unit_types = parsed_args.models.keys()
        for unit_type in self.unit_types:
            for dirpath, dirnames, filenames in os.walk(
                    '/var/lib/pulp/content/units/%s' % unit_type):
                for filename in filenames:
                    self.paths.add(path.join(dirpath, filename))

    @validator.MultiValidator.affects_repositories(
        failure_factory=DownloadedFileContentUnitValidator.failure_factory)
    def validate(self, unit, *args):
        """Check the unit.

        Remove unit.storage_path from self.filenames to account for every filename under
        /var/lib/pulp/content/units/

        :param unit: the unit to check
        :type unit: pulp.server.db.model.FileContentUnit
        :param args: unused
        :returns: None
        :raises: MISSING_ERROR
        """
        # A FileContentUnit has exactly a single storage path
        try:
            self.paths.remove(unit.storage_path)
        except KeyError:
            # double remove should not happen
            raise MISSING_ERROR

    @property
    def results(self):
        """Report unpaired filenames as dark content.

        :returns: an iterable over DarkPath validation results
        """
        for storage_path in self.paths:
            yield validator.DarkPath(self, storage_path, DARK_CONTENT)
