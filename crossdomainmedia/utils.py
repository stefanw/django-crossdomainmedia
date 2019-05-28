from urllib.parse import parse_qs, urlsplit, urlunsplit

from django.http import HttpResponse
from django.utils.http import urlencode


def strip_path(url):
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    return urlunsplit((str(scheme), str(netloc), '', '', ''))


def add_token(url, sign_func, token_name):
    """
    Given a URL, apply sign_func to path and add
    result as `token_name` to query parameters
    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    token = sign_func(path)
    query_params = parse_qs(query_string)
    query_params.update({token_name: token})
    new_query_string = urlencode(query_params, doseq=True)
    return urlunsplit((str(scheme), str(netloc), str(path),
                       str(new_query_string), str(fragment)))


def send_internal_file(url):
    response = HttpResponse()
    # Content-Type is filled in by nginx
    response['Content-Type'] = ""
    response['X-Accel-Redirect'] = url
    return response
