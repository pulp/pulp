from pulp.server.db.model.auth import Permission


def migrate(*args, **kwargs):
    """
    Modify the permissions collection schema to allow '.' in usernames
    """
    collection = Permission.get_collection()
    for permission in collection.find({}):
        updated_permissions = []
        if isinstance(permission['users'], dict):
            for username, user_permission in permission['users'].items():
                new_permission = dict(username=username, permissions=user_permission)
                updated_permissions.append(new_permission)
            permission['users'] = updated_permissions
            collection.save(permission, safe=True)
