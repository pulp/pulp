from mongoengine.queryset import DoesNotExist, QuerySet
from pymongo import ASCENDING

from pulp.server import exceptions as pulp_exceptions


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
        model = query_set._document
        if hasattr(model, 'serializer'):
            criteria = model.serializer().translate_criteria(model, criteria)

        if criteria.spec is not None:
            query_set = query_set.filter(__raw__=criteria.spec)

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


class RepoQuerySet(CriteriaQuerySet):
    """
    Custom queryset for repositories.
    """

    def get_repo_or_missing_resource(self, repo_id):
        """
        Allows a django-like get or 404.

        :param repo_id: identifies the repository to be returned
        :type  repo_id: str

        :return: repository object
        :rtype:  pulp.server.db.models.Repository

        :raises pulp_exceptions.MissingResource if repository is not found
        """
        try:
            return self.get(repo_id=repo_id)
        except DoesNotExist:
            raise pulp_exceptions.MissingResource(repository=repo_id)
