from rest_framework import pagination


class UUIDPagination(pagination.CursorPagination):
    """
    Paginate an API view naively, based on the UUID of objects being iterated over.

    This assumes that the objects being iterated over have an 'id' field, that the value of this
    field is a UUID, and that the field is indexed.

    This assumption should be True for all Models inheriting `pulpcore.app.models.Model`, the Pulp
    base Model class.

    """
    ordering = 'id'


class NamePagination(pagination.CursorPagination):
    """
    Paginate an API view based on the value of the 'name' field of objects being iterated over.

    This Paginator should be used for any model that has a 'name' field and requires a value,
    allowing for a more obvious and user-friendly pagination than the default by-uuid pagination.

    """
    ordering = 'name'
