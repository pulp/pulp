from gettext import gettext as _

from pulpcore.app import models

# pulpcore.serializers is still initializing, so the pulpcore.serializers namespace isn't
# importable. fields loads after base, so bring it in with a relative import
from . import base


class ConfigKeyValueRelatedField(base.GenericKeyValueRelatedField):
    help_text = _('A mapping of string keys to string values, for configuring this object.')
    required = False
    queryset = models.Config.objects.all()


class NotesKeyValueRelatedField(base.GenericKeyValueRelatedField):
    help_text = _('A mapping of string keys to string values, for storing notes on this object.')
    required = False
    queryset = models.Notes.objects.all()


class ScratchpadKeyValueRelatedField(base.GenericKeyValueRelatedField):
    help_text = _('A mapping of string keys to string values, for storing an arbitrary information '
                  'of this object.')
    required = False
    queryset = models.Scratchpad.objects.all()
