import json

from django.views.generic import View

from pulp.common import tags
from pulp.server.auth.authorization import EXECUTE
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as manager_factory
from pulp.server.tasks import repository
from pulp.server.webservices.controllers.decorators import auth_required


class RepoSync(View):

    @auth_required(EXECUTE)
    def post(self, request, repo_id):

        # Params
        try:
            params = json.loads(request.body)
        except ValueError:
            params = {}
        overrides = params.get('override_config', None)

        # Check for repo existence and let the missing resource bubble up
        manager_factory.repo_query_manager().get_repository(repo_id)

        # Execute the sync asynchronously
        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('sync')]
        async_result = repository.sync_with_auto_publish.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id, overrides], {}, tags=task_tags)

        # this raises an exception that is handled by the middleware,
        # so no return is needed
        raise exceptions.OperationPostponed(async_result)
