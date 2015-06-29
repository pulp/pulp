from mongoengine.queryset import QuerySet
from pymongo import ASCENDING


class CriteriaQuerySet(QuerySet):
    """
    This class defines a custom QuerySet to support searching by Criteria object
    which is a Pulp custom query object.

    This can be set to the 'queryset_class' attribute of the 'meta' directory
    in the model classes inherited from mongoengine.Document. See TaskStatus model
    for reference.
    """

    def find_by_criteria(self, criteria):
        """
        Run a query with a Pulp custom query object
        :param criteria: Criteria object specifying the query to run
        :type  criteria: pulp.server.db.model.criteria.Criteria
        :return: mongoengine queryset object
        :rtype:  mongoengine.queryset.QuerySet
        """
        query_set = self
        if criteria.spec is not None:
            query_set = query_set.filter(**criteria.spec)

        if criteria.fields is not None:
            query_set = query_set.only(*criteria.fields)

        sort_list = []
        if criteria.sort is not None:
            for (sort_by, order) in criteria.sort:
                if order == ASCENDING:
                    sort_list.append("+" + sort_by)
                else:
                    sort_list.append("-" + sort_by)
            if sort_list:
                query_set = query_set.order_by(*sort_list)

        if criteria.skip is not None:
            query_set = query_set.skip(criteria.skip)

        if criteria.limit is not None:
            query_set = query_set.limit(criteria.limit)

        return query_set

    def update(self, *args, **kwargs):
        """
        This method emulates post_save() on Documents.

        It attempts to call post_save() on each Document in the query set. If
        post_save() does not exist, it will do nothing.

        """
        super(CriteriaQuerySet, self).update(*args, **kwargs)
        for doc in self:
            try:
                doc.post_save(type(doc).__name__, doc)
            except AttributeError:
                # if post_save() is not defined for this particular document, that's ok
                pass
