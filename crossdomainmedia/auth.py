import os
from django.conf import settings
from django.core.signing import (
    TimestampSigner, SignatureExpired, BadSignature
)
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_permission_codename

from .utils import (
    add_token, strip_path, send_internal_file
)


class CrossDomainMediaAuthException(Exception):
    pass


class MissingToken(CrossDomainMediaAuthException):
    pass


class ExpiredToken(CrossDomainMediaAuthException):
    pass


class BadToken(CrossDomainMediaAuthException):
    pass


class CrossDomainMediaAuth:
    SIGNING_SEPARATOR = ':'
    TOKEN_NAME = 'token'
    TOKEN_MAX_AGE_SECONDS = 2 * 60
    PERMISSION = 'view'
    SITE_URL = None
    DEBUG = settings.DEBUG

    def __init__(self, context):
        self.context = context

    def is_media_public(self):
        '''
        Determine if the media described by self.context
        needs authentication/authorization at all
        '''
        raise NotImplementedError  # pragma: no cover

    def get_auth_url(self):
        '''
        Give URL path to authenticating view
        for the media described in context
        '''
        raise NotImplementedError  # pragma: no cover

    def get_media_file_path(self):
        '''
        Return the file path relative to MEDIA_ROOT
        '''
        raise NotImplementedError  # pragma: no cover

    def get_site_url(self):
        return self.SITE_URL or settings.SITE_URL

    def get_media_url_path(self):
        return self.get_auth_url()

    def get_media_url(self):
        '''
        Only use domain part of MEDIA_URL if it exists
        '''
        return strip_path(settings.MEDIA_URL) + self.get_media_url_path()

    def get_internal_media_prefix(self):
        return getattr(settings, 'INTERNAL_MEDIA_PREFIX', '/protected')

    def is_debug(self):
        return settings.DEBUG

    def get_media_internal_url_path(self):
        '''
        Return the internal URL path for nginx to the actual media file
        '''
        return os.path.join(
            self.get_internal_media_prefix(),
            self.get_media_file_path()
        )

    def has_perm(self, request):
        '''
        Default implementation checks if user
        has view permission
        '''

        user = request.user
        obj = self.context['object']
        opts = obj.__class__._meta
        codename = get_permission_codename(self.PERMISSION, opts)
        return user.has_perm('{app_label}.{codename}'.format(
            app_label=opts.app_label,
            codename=codename
        ), obj=obj)

    def get_full_auth_url(self):
        '''
        Return full URL with web domain
        '''
        return self.get_site_url() + self.get_auth_url()

    def get_authorized_internal_path(self, request):
        try:
            if not self.is_media_public():
                self.check_token_request(request)
            return self.get_media_internal_url_path()
        except Exception:
            raise

    def get_file_path(self, request):
        '''
        In DEBUG mode check permission or token
        '''
        if self.is_media_public() or self.has_perm(request):
            return self.get_media_file_path()
        try:
            self.check_token_request(request)
            return self.get_media_file_path()
        except Exception:
            raise PermissionDenied

    def get_full_media_url(self, authorized=False):
        url = self.get_media_url()
        if authorized:
            url = self.add_token(url)
        return url

    def get_authorized_media_url(self, request):
        if self.is_media_public():
            return self.get_full_media_url(authorized=False)
        if self.has_perm(request):
            return self.get_full_media_url(authorized=True)
        raise PermissionDenied

    def get_signer(self):
        return TimestampSigner(sep=self.SIGNING_SEPARATOR)

    def sign_path(self, path):
        path = self.get_path_to_sign(path)
        SEP = self.SIGNING_SEPARATOR
        signer = self.get_signer()
        return SEP.join(signer.sign(path).rsplit(SEP, 2)[-2:])

    def add_token(self, url):
        return add_token(
            url,
            self.sign_path,
            self.TOKEN_NAME
        )

    def get_path_to_sign(self, path):
        return path

    def get_token(self, request):
        return request.GET.get(self.TOKEN_NAME)

    def get_token_max_age(self):
        return self.TOKEN_MAX_AGE_SECONDS

    def check_token_request(self, request):
        token = self.get_token(request)
        return self.check_token(token)

    def check_token(self, token):
        if token is None:
            raise MissingToken()

        path = self.get_path_to_sign(
            self.get_media_url_path()
        )
        # Reconstruct original signature
        original = '{}:{}'.format(path, token)
        signer = self.get_signer()
        max_age = self.get_token_max_age()
        try:
            return signer.unsign(original, max_age=max_age)
        except SignatureExpired:
            raise ExpiredToken()
        except BadSignature:
            raise BadToken()

    def send_internal_file(self):
        return send_internal_file(
            self.get_media_internal_url_path()
        )
