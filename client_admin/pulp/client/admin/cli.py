from pulp.client.extensions.decorator import priority
from pulp.client.admin import (
    admin_auth, consumer, content, auth, binding, event, orphan, repo,
    server_info, tasks)


@priority()
def initialize(context):
    admin_auth.initialize(context)
    consumer.initialize(context)
    content.initialize(context)
    auth.initialize(context)
    binding.initialize(context)
    event.initialize(context)
    orphan.initialize(context)
    repo.initialize(context)
    server_info.initialize(context)
    tasks.initialize(context)
