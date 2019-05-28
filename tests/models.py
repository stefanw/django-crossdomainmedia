from django.db import models


class Attachment(models.Model):
    name = models.CharField(max_length=255)
    public = models.BooleanField(default=False)
    file = models.FileField()

    def get_crossdomain_auth(self):
        from .views import AttachmentCrossDomainMediaAuth

        return AttachmentCrossDomainMediaAuth({
            'object': self,
        })
