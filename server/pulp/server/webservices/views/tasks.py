from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.webservices.views.base import generate_django_response
from pulp.server.webservices.controllers.decorators import auth_required


class TasksView(View):

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        return generate_django_response(HttpResponse, """{"foo": "bar"}""")
