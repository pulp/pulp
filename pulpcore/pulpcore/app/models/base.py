import uuid

from django.db import models
from django.db.models import options


class Model(models.Model):
    """Base model class for all Pulp models.

    Uses UUID as its primary key field, named "id" to mimic default Django model
    behavior.

    Fields:
        id: UUID ID Primary Key Field

    References:

        * https://docs.djangoproject.com/en/1.8/topics/db/models/#automatic-primary-key-fields
        * https://docs.djangoproject.com/en/1.8/ref/models/fields/#uuidfield
        * https://www.postgresql.org/docs/current/static/datatype-uuid.html

    """
    # ...we have zero interest in using a mongo-specific datatype (ObjectId) as
    # the django PK, but it is possible to convert ObjectIds to UUIDs if we want to
    # maintain PKs from mongo to postgres.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    def __str__(self):
        try:
            # if we have a name, use it
            return '<{}: {}>'.format(self._meta.object_name, self.name)
        except AttributeError:
            # if we don't, use the pk
            return '<{}: pk={}>'.format(self._meta.object_name, self.pk)

    def __repr__(self):
        return str(self)


class MasterModel(Model):
    """Base model for the "Master" model in a "Master-Detail" relationship.

    Provides methods for casting down to detail types, back up to the master type,
    as well as a model field for tracking the type.

    Attributes:

        TYPE (str): Default constant value saved into the ``type``
            field of Model instances

    Fields:

        type: The user-facing string identifying the detail type of this model

    Warning:
        Subclasses of this class rely on there being no other parent/child Model
        relationships than the Master/Detail relationship. All subclasses must use
        only abstract Model base classes for MasterModel to behave properly.
        Specifically, OneToOneField relationships must not be used in any MasterModel
        subclass.

    """

    # TYPE is the user-facing string that describes this type. It is used to construct API
    # endpoints for Detail models, and will be seen in the URLs generated for those Detail models.
    # It can also be used for filtering across a relation where a model is related to a Master
    # model. Set this to something reasonable in Master and Detail model classes, e.g. when
    # create a master model, like "Importer", its TYPE value could be "importer". Then, when
    # creating an Importer Detail class like PackageImporter, its type value could be "package",
    # not "package_importer", since "package_importer" would be redundant in the context of
    # an importer Master model.
    TYPE = None

    # This field must have a value when models are saved, and defaults to the value of
    # the TYPE attribute on the Model being saved (seen above).
    type = models.TextField(null=False, default=None)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # instances of "detail" models that subclass MasterModel are exposed
        # on instances of MasterModel by the string stored in that model's TYPE attr.
        # Storing this type in a column on the MasterModel next to makes it trivial
        # to filter for specific detail model types across master's relations.
        if not self.type:
            self.type = self.TYPE
        return super(MasterModel, self).save(*args, **kwargs)

    def cast(self):
        """Return a "Detail" model instance of this master-detail pair.

        If this model is already an instance of its detail type, it will return itself.
        """
        # Go through our related objects, find the one that's a subclass of this model
        # on a OneToOneField, which identifies it as a potential detail relation.
        for rel in self._meta.related_objects:
            if rel.one_to_one and issubclass(rel.related_model, self._meta.model):
                # The name of this relation is the name of the attr on the model instance.
                # If that attr as a value, that means a row exists for this model in the
                # related detail table. Cast and resturn this value, recursively following
                # master/detail relationships down to the last table (the most detailed).
                try:
                    return getattr(self, rel.name).cast()
                except AttributeError:
                    continue
        else:
            # The for loop exited normally, there are no more detailed models than this
            # one in this instance's master/detail ancestry, so return here.
            return self

    @property
    def master(self):
        """The "Master" model instance of this master-detail pair

        If this is already the master model instance, it will return itself.
        """
        if self._meta.master_model:
            return self._meta.master_model(pk=self.pk)
        else:
            return self

    def __str__(self):
        # similar to Model's __str__, but type-aware
        cast = self.cast()
        if cast is self:
            return super(MasterModel, self).__str__()

        try:
            return '<{} (type={}): {}>'.format(self._meta.object_name, cast.TYPE, cast.name)
        except AttributeError:
            return '<{} (type={}): pk={}>'.format(self._meta.object_name, cast.TYPE, cast.pk)


# Add properties to model _meta info to support master/detail models
# If this property is not None on a Model, then that Model is a Detail Model.
# Doing this in a non-monkeypatch way would mean a lot of effort to achieve the same result
# (e.g. custom model metaclass, custom Options implementation, etc). These could be classmethods
# on Model classes, but it's easy enough to use the model's _meta namespace to do this, since
# that's where other methods like this exist in Django.
def master_model(options):
    """
    The Master model class of this Model's Master/Detail relationship.

    Accessible at ``<model_class>._meta.master_model``, the Master model class in a Master/Detail
    relationship is the most generic non-abstract Model in this model's multiple-table chain
    of inheritance.

    If this model is not a detail model, None will be returned.
    """
    # If this isn't even a MasterModel descendant, don't bother.
    if not issubclass(options.model, MasterModel):
        return None
    try:
        # The last item in this list is the oldest ancestor. Since the MasterModel usage
        # is to declare your master by subclassing MasterModel, and MasterModel is abstract,
        # the oldest ancestor model is the Master Model.
        return options.get_parent_list()[-1]
    except IndexError:
        # Also None if this model is itself the master.
        return None


options.Options.master_model = property(master_model)
