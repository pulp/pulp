from pulp.server.db.model.auth import Role


def migrate(*args, **kwargs):
    """
    Move role permissions into the permissions database
    """
    collection = Role.get_collection()
    for role in collection.find({}):
        updated_permissions = []
        if isinstance(role['permissions'], dict):
            for resource, permission in role['permissions'].items():
                resource_permission = dict(resource=resource, permission=permission)
                updated_permissions.append(resource_permission)
            role['permissions'] = updated_permissions
            collection.save(role)
