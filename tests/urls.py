from django.conf.urls import url

from .views import AttachmentFileDetailView, ExpiredAttachmentFileDetailView

urlpatterns = [
    url(r'^attachment/(?P<name>.+)',
        AttachmentFileDetailView.as_view(),
        name='attachment_file'),
    url(r'^attachment-expired/(?P<name>.+)',
        ExpiredAttachmentFileDetailView.as_view(),
        name='attachment_file_expired')
]
