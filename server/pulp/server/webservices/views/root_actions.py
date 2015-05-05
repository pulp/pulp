from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import generate_json_response


class LoginView(View):
    """
    View for API root-level actions.
    """

    @auth_required(authorization.READ)
    def post(self, request):
        """
        Return client SSL certificate and a private key.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :return: Response containing cert and key
        :rtype: django.http.HttpResponse
        """
        user = factory.principal_manager().get_principal()
        key, certificate = factory.cert_generation_manager().make_admin_user_cert(user)
        key_cert = {'key': key, 'certificate': certificate}
        return generate_json_response(key_cert)
