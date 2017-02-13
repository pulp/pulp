from datetime import datetime, timedelta
from gettext import gettext as _
import operator

from mongoengine import Q
from mongoengine.queryset import DoesNotExist, QuerySetNoCache
from pymongo import ASCENDING

from pulp.common import constants
from pulp.common.dateutils import ensure_tz
from pulp.server import exceptions as pulp_exceptions


class QuerySetPreventCache(QuerySetNoCache):
    """
    All custom QuerySet classes should inherit from this class rather than QuerySet
    or QuerySetNoCache. There are two reasons for this. Firstly, all QuerySets should
    not cache their query results by default, so QuerySetNoCache must be inherited.
    Secondly, QuerySetNoCache's implementation of the `cache` instance method
    explicitly returns an instance of QuerySet which effectively removes any
    customized behavior for that QuerySet.
    """

    def cache(self):
        """
        Currently, there is no reason to have a caching version of any of our
        custom QuerySet classes. If that ever changes, this method should be
        implemented to return a caching version of the custom QuerySet. This
        implementation exists in order to avoid bugs resulting from the
        unexpected default behavior of `cache`.

        As of mongoengine 0.10, the default implementation of ``cache`` cannot
        be used as it explicitly creates a QuerySet object, thus removing any
        custom behavior of the custom QuerySet.
        """
        msg = _('In order to support caching QuerySets, you must implement the'
                ' cache method on ' + self.__class__.__name__)
        raise NotImplementedError(msg)


class CriteriaQuerySet(QuerySetPreventCache):
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
        if hasattr(model, 'SERIALIZER'):
            criteria = model.SERIALIZER().translate_criteria(model, criteria)

        if criteria.spec is not None:
            query_set = query_set.filter(__raw__=criteria.spec)

        if criteria.fields is not None:
            # if limiting the fields, we should always include the id, but id must be added after
            # the translate because we don't want this turned into _id.
            if 'id' not in criteria.fields:
                criteria.fields.append('id')
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

    def get_or_404(self, **kwargs):
        """
        Generally allow querysets to raise a MissingResource exception if getting an object that
        does not exist.

        :param kwargs: keyword arguments that specify field of the document and value it should be
        :raise pulp_exceptions.MissingResource: if no objects are found
        """
        try:
            return self.get(**kwargs)
        except DoesNotExist:
            raise pulp_exceptions.MissingResource(**kwargs)


class WorkerQuerySet(CriteriaQuerySet):
    """
    Custom queryset for workers
    """

    def get_online(self):
        """
        Returns a queryset with a subset of Worker documents.

        The queryset is filtered to remove any Worker document that has not been updated in the
        last 25 seconds.

        :return: mongoengine queryset object
        :rtype:  mongoengine.queryset.QuerySet
        """
        query_set = self
        now = ensure_tz(datetime.utcnow())
        oldest_heartbeat_time = now - timedelta(seconds=constants.PULP_PROCESS_TIMEOUT_INTERVAL)
        return query_set.filter(last_heartbeat__gte=oldest_heartbeat_time)


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
        :rtype:  pulp.server.db.model.Repository

        :raises pulp_exceptions.MissingResource if repository is not found
        """
        try:
            return self.get(repo_id=repo_id)
        except DoesNotExist:
            raise pulp_exceptions.MissingResource(repository=repo_id)


class RepositoryContentUnitQuerySet(CriteriaQuerySet):
    """
    Custom queryset for repository content units.
    """

    def _num_between(self, field, start=None, end=None, repo_id=None):
        """
        Helper function to query units of based on timestamps.

        :param field: date field that will be searched
        :type  field: str
        :param start: find units in which the specified field is after this time
        :type  start: str in ISO8601 format with timezone
        :param end: find units in which the specified field is before this time
        :type  end: str in ISO8601 format with timezone
        :param repo_id: restrict search to this repo
        :type  repo_id: str
        :return: number of units in the repo in which the specified field is between start and end
        :rtype:  int
        """
        q_dicts = []

        if end is not None:
            q_dicts.append({field + "__lte": end})

        if start is not None:
            q_dicts.append({field + "__gte": start})

        if repo_id is not None:
            q_dicts.append({"repo_id": repo_id})

        Q_filters = [Q(**q_dict) for q_dict in q_dicts]
        query = reduce(operator.and_, Q_filters)

        return self(query).count()

    def num_created(self, start=None, end=None, repo_id=None):
        """
        Find the number of content units that were created in between the start and end times.

        :param start: find units created after this time
        :type  start: str in ISO8601 format with timezone
        :param end: find units created before this time
        :type  end: str in ISO8601 format with timezone
        :param repo_id: restrict search to this repo
        :type  repo_id: str
        :return: number of units created between start and end of the specified repo
        :rtype:  int
        """
        return self._num_between("created", start, end, repo_id)

    def num_updated(self, start=None, end=None, repo_id=None):
        """
        Find the number of content units that were updated in between the start and end times.

        :param start: find units updated after this time
        :type  start: str in ISO8601 format with timezone
        :param end: find units updated before this time
        :type  end: str in ISO8601 format with timezone
        :param repo_id: restrict search to this repo
        :type  repo_id: str
        :return: number of units updated between start and end of the specified repo
        :rtype:  int
        """
        return self._num_between("updated", start, end, repo_id)
