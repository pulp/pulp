import json

from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.controllers.decorators import auth_required


class DistributorResourceView(View):
    pass


class DistributorsView(View):
    pass


class ImporterResourceView(View):
    pass


class ImportersView(View):
    pass


class TypeResourceView(View):
    pass


class TypesView(View):
    pass
