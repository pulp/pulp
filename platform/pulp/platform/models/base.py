import uuid

from django.db import models

__all__ = [
    'Model',
    'MasterModel',
]


class Model(models.Model):
    """Base model class for all Pulp models.

    Uses UUID as its primary key field, named "id" to mimic default Django model
    behavior.

    References:
        https://docs.djangoproject.com/en/1.8/topics/db/models/#automatic-primary-key-fields
        https://docs.djangoproject.com/en/1.8/ref/models/fields/#uuidfield
        https://www.postgresql.org/docs/current/static/datatype-uuid.html
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # ...we have zero interest in using a mongo-specific datatype (ObjectId) as
    # the django PK.

    class Meta:
        abstract = True


class MasterModelQuerySet(models.QuerySet):
    # a normal django queryset, but adds the 'cast' method to the QuerySet DSL,
    # which runs the cast method on the current queryset, returning detail instances
    def cast(self):
        return (instance.cast() for instance in self)

# Make a Manager class based on the cast-aware queryset
MasterModelManager = models.Manager.from_queryset(MasterModelQuerySet)


class MasterModel(Model):
    """Base model for the "Master" model in a "Master-Detail" relationship.

    Provides methods for casting down to detail types, back up to the master type,
    as well as a model field for tracking the type.

    Warning:
        Subclasses of this class rely on there being no other parent/child Model
        relationships than the Master/Detail relationship. All subclasses must use
        only abstract Model base classes for MasterModel to behave properly.
        Specifically, OneToOneField relationships must not be used in any MasterModel
        subclass.

    """
    detail_model = models.CharField(max_length=63)

    objects = MasterModelManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # instances of "detail" models that subclass MasterModel are exposed
        # on instances of MasterModel by a lowercase version of their model
        # name. That name is what I'm using here to determine the value of
        # type. Storing type in a column on the MasterModel next to makes it trivial
        # to filter for specific detail model types across model relations.
        if not self.detail_model:
            self.detail_model = self._meta.model_name
        return super(MasterModel, self).save(*args, **kwargs)

    def cast(self):
        """Return a "Detail" model instance of this master-detail pair.

        If this model is already an instance of its detail type, it will return itself.
        """
        # If this instance's type matches the current model name, it is already cast. Return it.
        if self.detail_model == self._meta.model_name:
            return self
        else:
            try:
                # Otherwise, return the cast model attribute for this instance
                return getattr(self, self.detail_model)
            except AttributeError:
                # Unknown content type. The generic content type is as specific as
                # we can get here. This is a great place to throw a log message about
                # encountering an un-modelled type, such as a type from an uninstalled
                # plugin.
                return self

    @property
    def master(self):
        """The "Master" model instance of this master-detail pair

        If this is already the master model instance, it will return itself.
        """
        # The assumption here is that the first OneToOneField found is the master
        # related field. Based on testing, additional layers of nested inheritance
        # add their their fields to the bottom of the model's field list.
        # XXX This is potentially unreliable, and should absolutely be covered by unit tests.
        #     This is also the reason for the warning issued in MasterModel's docstring.
        for field in self._meta.fields:
            if type(field) is models.OneToOneField:
                return getattr(self, field.name)
        else:
            # No OneToOneField means this is already the master.
            return self

    def __repr__(self):
        return '<{} "{}">'.format(type(self).__name__, str(self))
