from .base import register_datanode, register_viewgroup, SelfLoading, MultiValue, Directory, DataNode, _join_plex
from six.moves.urllib import parse

import imghdr
import base64
import requests


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
        img = ImgHelper(self, value)
        setattr(self, '_img_%s' % attr, img)
        return img
    return property(__inner)


@register_viewgroup('Video')
class VideoItem(SelfLoading, MultiValue, Directory):
    thumb = image_getter('thumb')
    art = image_getter('art')


@register_viewgroup('Media')
@register_datanode('Media')
class MediaItem(DataNode):
    pass


@register_datanode('Part')
class PartItem(DataNode):
    pass


@register_datanode('Stream')
class StreamItem(DataNode):
    pass


@register_viewgroup('Genre')
class GenreItem(DataNode):
    pass


@register_viewgroup('Role')
class RoleItem(DataNode):
    thumb = image_getter('thumb')


@register_viewgroup('Director')
class DirectorItem(DataNode):
    pass


@register_viewgroup('Writer')
class WriterItem(DataNode):
    pass


@register_viewgroup('Producer')
class ProducerItem(DataNode):
    pass


@register_viewgroup('Collection')
class CollectionItem(DataNode):
    pass
