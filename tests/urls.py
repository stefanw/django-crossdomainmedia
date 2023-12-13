from django.urls import re_path

from .views import AttachmentFileDetailView, ExpiredAttachmentFileDetailView

urlpatterns = [
    re_path(
        r"^attachment/(?P<name>.+)",
        AttachmentFileDetailView.as_view(),
        name="attachment_file",
    ),
    re_path(
        r"^attachment-expired/(?P<name>.+)",
        ExpiredAttachmentFileDetailView.as_view(),
        name="attachment_file_expired",
    ),
]
