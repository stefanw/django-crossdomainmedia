from django.views.generic import DetailView
from django.urls import reverse
from django.shortcuts import get_object_or_404

from crossdomainmedia import CrossDomainMediaMixin, CrossDomainMediaAuth

from .models import Attachment


class CustomCrossDomainMediaAuth(CrossDomainMediaAuth):
    URL_NAME = 'attachment_file'

    def is_media_public(self):
        '''
        Determine if the media described by self.context
        needs authentication/authorization at all
        '''
        return self.context['object'].public

    def get_auth_url(self):
        '''
        Give URL path to authenticating view
        for the media described in context
        '''
        obj = self.context['object']
        return reverse(self.URL_NAME, kwargs={'name': obj.name})

    def get_media_file_path(self):
        '''
        Return the file path relative to MEDIA_ROOT to serve in debug mode
        '''
        obj = self.context['object']
        return obj.file.name


class ExpiredCustomCrossDomainMediaAuth(CustomCrossDomainMediaAuth):
    TOKEN_MAX_AGE_SECONDS = 0
    URL_NAME = 'attachment_file_expired'


class AttachmentFileDetailView(CrossDomainMediaMixin, DetailView):
    media_auth_class = CustomCrossDomainMediaAuth

    def get_object(self):
        return get_object_or_404(Attachment, name=self.kwargs['name'])


class ExpiredAttachmentFileDetailView(AttachmentFileDetailView):
    media_auth_class = ExpiredCustomCrossDomainMediaAuth
