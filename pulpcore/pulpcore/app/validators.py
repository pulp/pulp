from rest_framework.validators import UniqueValidator, qs_exists
from pulpcore.exceptions.http import ConflictError
from gettext import gettext as _


class PulpUniqueValidator(UniqueValidator):
    """
    Redefinition of UniqueValidator.

    When unique constraint is violated conflict exception is raised.
    """

    def __call__(self, value):
        queryset = self.queryset
        queryset = self.filter_queryset(value, queryset)
        queryset = self.exclude_current_instance(queryset)
        detail = {self.field_name: [_('This field must be unique.')]}
        if qs_exists(queryset):
            raise ConflictError(detail)
