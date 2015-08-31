from __future__ import unicode_literals, absolute_import
from collections import defaultdict

import requests
import six
from six.moves.urllib import parse

from . import exceptions

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET


def _join_plex(x, y):
    url = parse.urljoin(x, y)
    if not url.endswith('/'):
        url = url + '/'
    return url


class RequestBase(object):
    element_types = {}
    subelement_types = defaultdict(dict)

    def __init__(self, base, relative=None, xml=None):
        self._xml = None
        self._has_token = False
        self._url = None
        self._data = {} if xml is None else dict(xml.attrib.items())
        self._title = self._data.pop('title', None)
        self._items = []
        self._key = None
        self._index = None
        try:
            self._index = int(self._data.get('index'))
        except:
            pass
        if isinstance(base, six.string_types):
            base_url = base
        elif isinstance(base, RequestBase):
            base_url = base.url
            self._has_token = base.has_token
        scheme, netloc, path, qs, fragment = parse.urlsplit(base_url)
        if relative:
            self._key = relative
            path = _join_plex(path, relative)
        if not self._has_token:
            self._has_token = 'X-Plex-Token' in parse.parse_qs(qs)
        self._url = parse.urlunsplit((scheme, netloc, path, qs, fragment))

    def __repr__(self):
        if self._title:
            return "<%s: %s>" % (self.__class__.__name__, self._title)
        return "<%s>" % (self.__class__.__name__)

    def __getitem__(self, key):
        for item in self.items:
            if key in (item.title, item.key, item.index):
                return item

    @property
    def index(self):
        return self._index

    @property
    def data(self):
        return self._data

    @property
    def title(self):
        return self._title

    @property
    def key(self):
        return self._key

    @property
    def url(self):
        return self._url

    @property
    def has_token(self):
        return self._has_token

    @property
    def xml(self):
        if self._xml is not None:
            return self._xml
        resp = requests.get(self.url)
        if resp.status_code == 401:
            if not self.has_token:
                raise exceptions.TokenRequiredException()
            raise exceptions.InvalidTokenException()
        self._xml = ET.fromstring(resp.content)
        return self.xml

    @property
    def items(self):
        if self._items:
            return self._items
        xml = self.xml
        self._data.update(xml.attrib)
        self._items = []
        for item in xml.xpath('//MediaContainer/*'):
            cls = self._get_element_type(item)
            key = item.attrib.pop('key')
            self._items.append(cls(base=self, relative=key, xml=item))
        return self._items

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def get_element_class(self, el):
        return

    def _get_element_type(self, el):
        forced = self.get_element_class(el)
        if forced:
            return forced
        return self.__class__.find_element_type(el)

    @classmethod
    def find_element_type(cls, el):
        if el.tag in cls.subelement_types:
            subtype = el.attrib.get('type', None)
            options = cls.subelement_types[el.tag]
            if subtype in options:
                return options[subtype]
        if el.tag in cls.element_types:
            base = cls.element_types[el.tag]
            if issubclass(cls, base):
                if cls.subelement_type in cls.subelement_types.get(base.element_type):
                    return cls
        return RequestBase


def element_type(name):
    def _inner(x):
        RequestBase.element_types[name] = x
        setattr(x, 'element_type', name)
        return x
    return _inner


def sub_element(parent, typename):
    def _inner(x):
        RequestBase.subelement_types[parent][typename] = x
        setattr(x, 'subelement_type', typename)
        return x
    return _inner


@element_type('Directory')
class Directory(RequestBase):
    pass


@sub_element('Directory', 'movie')
class MovieDirectory(Directory):
    pass


@sub_element('Directory', 'show')
class SerieDirectory(Directory):
    def get_element_class(self, el):
        viewgroup = self.data.get('viewGroup', None)
        if viewgroup == 'season':
            if 'index' not in el.attrib:
                el.attrib['index'] = '-1'
            return SerieSeason


class SerieSeason(SerieDirectory):
    pass


@sub_element('Directory', 'artist')
class MusicDirectory(Directory):
    pass
