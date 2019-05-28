SECRET_KEY = "secretkey"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",

    "tests",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tests.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:"
    }
}

STATIC_URL = "/static/"

SITE_URL = 'https://www.example.com'
MEDIA_URL = 'https://media.example.org/media/'
INTERNAL_MEDIA_PREFIX = '/protected/'

SITE_DOMAIN = SITE_URL.replace('https://', '')
MEDIA_DOMAIN = MEDIA_URL.split('/')[2]

ALLOWED_HOSTS = (SITE_DOMAIN, MEDIA_DOMAIN, 'localhost')
