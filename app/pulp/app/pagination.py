from rest_framework import pagination


class UUIDPagination(pagination.CursorPagination):
    """
    Paginate an API view naively, based on the UUID of objects being iterated over.

    This assumes that the objects being iterated over have an 'id' field, that the value of this
    field is a UUID, and that the field is indexed.

    This assumption should be True for all Models inheriting `pulp.app.models.Model`, the Pulp base
    Model class.

    """
    ordering = 'id'
