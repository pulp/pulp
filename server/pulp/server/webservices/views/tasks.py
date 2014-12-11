from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.webservices.controllers.decorators import auth_required


class TasksView(View):

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        return HttpResponse("""{"foo": "bar"}""", content_type="application/json")
