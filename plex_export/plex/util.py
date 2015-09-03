from __future__ import unicode_literals, absolute_import
import base64
import imghdr
import requests
from six.moves.urllib import parse


def _join_plex(x, y):
    url = parse.urljoin(x, y)
    if not url.endswith('/'):
        url = url + '/'
    return url


class ImgHelper(object):
    def __init__(self, base, url):
        b_schema, b_netloc, b_path, b_qs, b_fragment = base._url_parts
        u_schema, u_netloc, u_path, u_qs, u_fragment = parse.urlsplit(url)
        self._path = url
        self._data = None
        self._data_type = None
        if u_netloc and u_netloc != b_netloc:
            self._url = url
        else:
            b_path = _join_plex(b_path, u_path)
            data = parse.parse_qsl(b_qs)
            b_qs = parse.urlencode([(x, y) for x, y in data if x == 'X-Plex-Token'])
            self._url = parse.urlunsplit((b_schema, b_netloc, b_path, b_qs, b_fragment))

    def load(self):
        if self._data:
            return
        response = requests.get(self._url)
        if not response.status_code == 200:
            return
        self._data = response.content
        self._data_type = imghdr.what(None, self._data)

    def base64_encoded(self):
        if not self.data:
            return
        return "data:image/%(dt)s;base64,%(b64)s" % {'dt': self._data_type, 'b64': base64.urlsafe_b64encode(self._data)}

    @property
    def url(self):
        return self._url

    @property
    def data(self):
        self.load()
        return self._data

    def __repr__(self):
        return "<Image: %s>" % (self._path)


def image_getter(attr):
    def __inner(self):
        img = getattr(self, '_img_%s' % attr, None)
        if img:
            return img
        value = self.get(attr)
        if not value:
            return None
        img = ImgHelper(self, value)
        setattr(self, '_img_%s' % attr, img)
        return img
    return property(__inner)
