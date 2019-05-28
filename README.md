# Cross-Domain Media with authentication for Django

**The situation**: You serve media files from a different domain than your main web application domain (good idea). You want to use [nginx's internal redirect (`X-Accel-Redirect`)](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal) to authorize media file delivery.

**The problem**:  You don't have access to the user's session on the media domain and can't authenticate or authorize media access.

**The solution**: You handle media URLs with an expiring token attached which temporarily authorizes access and can be refreshed via redirects when needed.


## HTTP View

Here's how it works in HTTP:

1. -> GET media.example.org/path/file.pdf
2. <- 302 www.example.com/path/file.pdf
3. -> GET www.example.com/path/file.pdf
    -  *if not authorized* <- 403
    -  *if authorized* <- 302 media.example.org/path/file.pdf?token=XYZ
4. -> GET media.example.org/path/file.pdf?token=XYZ
5. <- 200 file.pdf
6. *after expiry* -> GET media.example.org/path/file.pdf?token=XYZ
7. See step 2


## Use in Django

```python

# Development
MEDIA_URL = '/media/'

# Production

MEDIA_URL = 'https://media.example.org/media/
INTERNAL_MEDIA_PREFIX = '/protected/'
```


```python

from crossdomainmedia import (
    CrossDomainMediaAuth, CrossDomainMediaMixin
)


class CustomCrossDomainMediaAuth(CrossDomainMediaAuth):
    '''
    Create your own custom CrossDomainMediaAuth class
    and implement at least these methods
    '''
    SITE_URL = 'https://www.example.com'

    def is_media_public(self):
        '''
        Determine if the media described by self.context
        needs authentication/authorization at all
        '''
        return self.context['object'].is_public

    def get_auth_url(self):
        '''
        Give URL path to authenticating view
        for the media described in context
        '''
        obj = self.context['object']
        raise reverse('view-name', kwargs={'pk': obj.pk})

    def get_media_file_path(self):
        '''
        Return the file path relative to MEDIA_ROOT
        '''
        obj = self.context['object']
        return obj.file.name


class CustomDetailView(CrossDomainMediaMixin, DetailView):
    '''
    Add the CrossDomainMediaMixin
    and set your custom media_auth_class
    '''
    media_auth_class = CustomCrossDomainMediaAuth

```

### Some other useful methods

```python

# Get your media URLs with token outside of view
mauth = CustomCrossDomainMediaAuth({'object': obj})
mauth.get_full_media_url(authorized=True)

# Send file via nginx internal redirect response
mauth.send_internal_file()
```

## Nginx config

This is how an Nginx config could look like.

```nginx
server {
    # Web server with session on domain
    listen              443 ssl http2;
    server_name         www.example.com;
    # ...

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $host;
        # etc...

        proxy_pass wsgi_server;
    }
}

server {
    # Media server with no session on domain

    listen 443 ssl http2;
    server_name media.example.org;
    # ...

    location /media/ {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $host;
        # etc...

        proxy_pass wsgi_server;
    }

    location /protected {
        internal;

        alias /var/www/media-root;
    }
}
```
