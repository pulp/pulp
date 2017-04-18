"""
Utils for migrations.
"""

import logging

_logger = logging.getLogger(__name__)


MIGRATION_HEADER_MSG = '* Migrating %s content...'
MIGRATION_PROGRESS_MSG = '* Migrated units: %s of %s'
STARS = '*' * 79


class MigrationProgressLog(object):
    """
    Context manager that logs every 10% of migration completion.

    :ivar migrated_units: number of already migrated units
    :type migrated_units: int
    :ivar content_type: name of the content to be migrated
    :type content_type: str
    :ivar total_units: total number of units to be migrated
    :type total_units: int
    :ivar header_msg: message printed at the beginning of migration
    :type header_msg: str
    """
    migrated_units = 0

    def __init__(self, content_type, total_units, msg=MIGRATION_HEADER_MSG):
        self.content_type = content_type
        self.total_units = total_units
        self.msg = msg

    def __enter__(self):
        """
        Log a message indicating a start of migration process for a specific content.
        """
        if self.total_units:
            _logger.info(STARS)
            _logger.info(self.msg % self.content_type)

        return self

    def progress(self, msg=MIGRATION_PROGRESS_MSG):
        """
        Count migrated units and logs progress every 10%.
        Expected to be called for every migrated unit.
        """
        self.migrated_units += 1
        another_ten_percent_completed = self.total_units >= 10 and \
            not self.migrated_units % (self.total_units // 10)
        all_units_migrated = self.migrated_units == self.total_units
        if another_ten_percent_completed or all_units_migrated:
            _logger.info(msg % (self.migrated_units, self.total_units))

    def __exit__(self, *exc):
        """
        Print footer (or delimiter) to indicate the end of the content unit migration.
        """
        _logger.info(STARS)
