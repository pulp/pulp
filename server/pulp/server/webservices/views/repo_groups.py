import json

from django.http import HttpResponse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.controllers.decorators import auth_required


class RepoGroupsView(View):
    pass


class RepoGroupResourceView(View):
    pass


class RepoGroupAssociateView(View):
    pass


class RepoGroupUnassociateView(View):
    pass


class RepoGroupDistributorsView(View):
    pass


class RepoGroupDistributorResource(View):
    pass


class RepoGroupPublishView(View):
    pass

