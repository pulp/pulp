import json

from pulp.server.async.celery_instance import celery as pulp_celery

from celery.app import control
controller = control.Control(app=pulp_celery)


if __name__ == '__main__':
    active_queues = controller.inspect().active_queues()
    json_output = json.dumps(active_queues)
    print json_output
