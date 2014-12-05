from django.views.generic import View


class PulpView(View):
    def http_method_not_allowed(self, request, *args, **kwargs):
        pass