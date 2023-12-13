import os
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Attachment
from .views import CustomCrossDomainMediaAuth

User = get_user_model()


class CrossDomainMediaTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create(
            username="superuser", is_active=True, is_staff=True, is_superuser=True
        )
        self.superuser.set_password("password")
        self.superuser.save()

        self.public_attachment = Attachment.objects.create(
            name="public.txt", public=True, file="test_files/test-public.txt"
        )
        self.public_url = reverse(
            "attachment_file", kwargs={"name": self.public_attachment.name}
        )
        self.private_attachment = Attachment.objects.create(
            name="private.txt", public=False, file="test_files/test-private.txt"
        )
        self.private_url = reverse(
            "attachment_file", kwargs={"name": self.private_attachment.name}
        )

    def test_attachment_public(self):
        response = self.client.get(self.public_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.MEDIA_DOMAIN, response["Location"])

        response = self.client.get(
            response["Location"], HTTP_HOST=settings.MEDIA_DOMAIN
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Accel-Redirect", response)
        self.assertEqual(
            response["X-Accel-Redirect"],
            "%s%s" % (settings.INTERNAL_MEDIA_PREFIX, self.public_attachment.file.name),
        )

    def test_attachment_forbidden(self):
        response = self.client.get(self.private_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Location", response)
        self.assertNotIn("X-Accel-Redirect", response)

        response = self.client.get(self.private_url, HTTP_HOST=settings.MEDIA_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertIn("Location", response)

        self.assertEqual(
            response["Location"], "%s%s" % (settings.SITE_URL, self.private_url)
        )

        response = self.client.get(response["Location"], HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 403)

    def test_attachment_granted(self):
        loggedin = self.client.login(username="superuser", password="password")
        self.assertTrue(loggedin)
        response = self.client.get(self.private_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertIn("Location", response)
        self.assertNotIn("X-Accel-Redirect", response)

        url = response["Location"]
        self.assertIn("token=", url)

        response = self.client.get(url, HTTP_HOST=settings.MEDIA_DOMAIN)
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Accel-Redirect", response)

        self.assertEqual(
            response["X-Accel-Redirect"],
            "%s%s"
            % (settings.INTERNAL_MEDIA_PREFIX, self.private_attachment.file.name),
        )

    def test_attachment_token_expired(self):
        loggedin = self.client.login(username="superuser", password="password")
        self.assertTrue(loggedin)
        expiring_url = reverse(
            "attachment_file_expired", kwargs={"name": "private.txt"}
        )
        response = self.client.get(expiring_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertIn("Location", response)
        self.assertNotIn("X-Accel-Redirect", response)

        url = response["Location"]
        self.assertIn("token=", url)

        response = self.client.get(url, HTTP_HOST=settings.MEDIA_DOMAIN)
        # Token has expired
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertIn("Location", response)

        self.assertEqual(
            response["Location"], "%s%s" % (settings.SITE_URL, expiring_url)
        )
        response = self.client.get(expiring_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 302)

    def test_attachment_token_missing(self):
        loggedin = self.client.login(username="superuser", password="password")
        self.assertTrue(loggedin)
        response = self.client.get(self.private_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertIn("Location", response)
        self.assertNotIn("X-Accel-Redirect", response)

        url = response["Location"]
        self.assertIn("token=", url)
        # Remove token
        url = url.split("?token=")[0]

        response = self.client.get(url, HTTP_HOST=settings.MEDIA_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertIn("Location", response)

        self.assertEqual(
            response["Location"], "%s%s" % (settings.SITE_URL, self.private_url)
        )

    def test_attachment_token_broken(self):
        loggedin = self.client.login(username="superuser", password="password")
        self.assertTrue(loggedin)
        response = self.client.get(self.private_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 302)
        self.assertIn("Location", response)
        self.assertNotIn("X-Accel-Redirect", response)

        url = response["Location"]
        self.assertIn("token=", url)
        # Alter token
        url += "a"

        response = self.client.get(url, HTTP_HOST=settings.MEDIA_DOMAIN)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertNotIn("Location", response)

    @override_settings(
        DEBUG=True,
        SITE_URL="http://localhost:8000",
        MEDIA_URL="/media/",
        SITE_DOMAIN="localhost",
        MEDIA_ROOT=os.path.join(os.path.dirname(__file__)),
    )
    def test_debug_public(self):
        response = self.client.get(self.public_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        content = b"".join(list(response.streaming_content))
        self.assertEqual(content, b"public")

    @override_settings(
        DEBUG=True,
        SITE_URL="http://localhost:8000",
        MEDIA_URL="/media/",
        SITE_DOMAIN="localhost",
        MEDIA_ROOT=os.path.join(os.path.dirname(__file__)),
    )
    def test_debug_private(self):
        response = self.client.get(self.private_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b"")

    @override_settings(
        DEBUG=True,
        SITE_URL="http://localhost:8000",
        MEDIA_URL="/media/",
        SITE_DOMAIN="localhost",
        MEDIA_ROOT=os.path.join(os.path.dirname(__file__)),
    )
    def test_debug_private_allowed(self):
        loggedin = self.client.login(username="superuser", password="password")
        self.assertTrue(loggedin)

        response = self.client.get(self.private_url, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(response.status_code, 200)
        content = b"".join(list(response.streaming_content))
        self.assertEqual(content, b"private")

    def test_attachment_send_internal(self):
        mauth = CustomCrossDomainMediaAuth({"object": self.public_attachment})
        response = mauth.send_internal_file()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response)
        self.assertIn("X-Accel-Redirect", response)

        self.assertEqual(
            response["X-Accel-Redirect"],
            "%s%s" % (settings.INTERNAL_MEDIA_PREFIX, self.public_attachment.file.name),
        )

    def test_media_host_check(self):
        loggedin = self.client.login(username="superuser", password="password")
        self.assertTrue(loggedin)

        with self.settings(MEDIA_URL="https://media.www.example.com/media/"):
            MEDIA_DOMAIN = settings.MEDIA_URL.split("/")[2]
            response = self.client.get(self.public_url, HTTP_HOST=settings.SITE_DOMAIN)
            self.assertEqual(response.status_code, 302)
            self.assertIn("Location", response)
            parsed_url = urlparse(response["Location"])
            self.assertEqual(parsed_url.netloc, MEDIA_DOMAIN)
