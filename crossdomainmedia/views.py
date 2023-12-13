from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.static import serve

from .auth import BadToken, CrossDomainMediaAuth, ExpiredToken, MissingToken
from .utils import send_internal_file


class CrossDomainMediaMixin:
    media_auth_class = CrossDomainMediaAuth

    def is_media_host(self, mauth):
        media_host = urlparse(settings.MEDIA_URL).netloc
        return self.request.get_host() == media_host

    def invalid_token(self, mauth):
        return HttpResponse(status=403)

    def unauthorized(self, mauth):
        return HttpResponse(status=403)

    def refresh_token(self, mauth):
        return redirect(mauth.get_full_auth_url())

    def redirect_to_media(self, mauth):
        return redirect(mauth.get_authorized_media_url(self.request))

    def send_media_file(self, mauth):
        url = mauth.get_authorized_internal_path(self.request)
        return send_internal_file(url)

    def serve_media(self, mauth):
        url = mauth.get_file_path(self.request)
        return serve(self.request, url, settings.MEDIA_ROOT)

    def render_to_response(self, context):
        mauth = self.media_auth_class(context)

        if mauth.is_debug():
            return self.respond_debug(mauth)

        if self.is_media_host(context):
            return self.respond_media(mauth)
        return self.respond_web(mauth)

    def respond_debug(self, mauth):
        try:
            return self.serve_media(mauth)
        except PermissionDenied:
            return self.unauthorized(mauth)

    def respond_media(self, mauth):
        """
        Request on media host should either
        - serve the media
        - deny access
        - redirect back to app for authentication
        """
        try:
            return self.send_media_file(mauth)
        except ExpiredToken:
            return self.refresh_token(mauth)
        except MissingToken:
            return self.refresh_token(mauth)
        except BadToken:
            return self.invalid_token(mauth)

    def respond_web(self, mauth):
        """
        Request on web should always redirect or deny
        - redirect to media unauthorized for public access
        - redirect to media with token when authorized
        - deny when not authorized
        """

        try:
            return self.redirect_to_media(mauth)
        except PermissionDenied:
            return self.unauthorized(mauth)
