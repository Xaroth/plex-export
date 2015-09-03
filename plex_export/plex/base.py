from __future__ import unicode_literals, absolute_import

import requests
import six
from six.moves.urllib import parse

from .. import exceptions
from .util import _join_plex, image_getter

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET
try:
    from ..version_info import __version__
except ImportError:
    __version__ = '0.0.0'
NO_DEFAULT = object()

DEFAULT_HEADERS = {
    'X-Plex-Device-Name': 'plex-export (%s)' % __version__
}


class RequestBase(object):
    def __init__(self, base, relative=None):
        self._has_token = False
        self._url = None
        self._url_parts = None
        self._loaded = False
        self._xml = None
        self._url_parts = None
        self._headers = None
        if isinstance(base, six.string_types):
            base_url = base
            self._url_parts = list(parse.urlsplit(base_url))
        elif isinstance(base, RequestBase):
            base_url = base.url
            self._has_token = base.has_token
            self._url_parts = base._url_parts[:]
            self._headers = base._headers
        if relative:
            scheme, netloc, path, qs, fragment = parse.urlsplit(relative)
            if path:
                self._url_parts[2] = _join_plex(self._url_parts[2], path)
            if qs:
                data = parse.parse_qsl(self._url_parts[3]) + parse.parse_qsl(qs)
                self._url_parts[3] = parse.urlencode(data)
            else:
                # Strip of all non-token parts
                data = parse.parse_qsl(self._url_parts[3])
                self._url_parts[3] = parse.urlencode([(x, y) for x, y in data if x == 'X-Plex-Token'])
        if not self._has_token:
            self._has_token = 'X-Plex-Token' in parse.parse_qs(self._url_parts[3])
        self._url = parse.urlunsplit(self._url_parts)

    def __dir__(self):
        attrs = [x for x in self.__dict__.keys() if not x.startswith('_')]
        attrs.extend(dir(self.__class__))
        return list(set(attrs))

    def __repr__(self):
        scheme, netloc, path, qs, fragment = self._url_parts
        return "<%s: %s%s%s>" % (self.__class__.__name__, netloc, '' if path.startswith('/') else '/', path)

    @property
    def url(self):
        return self._url

    @property
    def has_token(self):
        return self._has_token

    def _request(self):
        return requests.get(self.url, headers=self._headers or DEFAULT_HEADERS)

    @property
    def xml(self):
        if self._xml is not None:
            return self._xml
        resp = self._request()
        if resp.status_code == 401:
            if not self.has_token:
                raise exceptions.TokenRequiredException()
            raise exceptions.InvalidTokenException()
        self._xml = ET.fromstring(resp.content)
        return self.xml

    def process_root(self, element):
        raise NotImplementedError()

    def process_element(self, element):
        raise NotImplementedError()

    def load(self):
        if self._loaded:
            return
        root = self.process_root(self.xml)
        for element in root.getchildren():
            self.process_element(element)


class BaseDirectory(RequestBase):
    _viewgroups = {}
    _keygroups = {}
    _default_viewgroup = None

    def __init__(self, base, relative=None):
        self._items = []
        self._itemsdict = {}
        self._child = self._default_viewgroup
        self._data = {}
        super(BaseDirectory, self).__init__(base, relative=relative)

    @property
    def indices(self):
        keys = ['key', 'type', 'title']
        bad_tokens = lambda x: '/' in x or '?' in x
        return [x for x in [self._data.get(key, None) for key in keys] if x and not bad_tokens(x)]

    def process_root(self, element):
        viewgroup = element.attrib.get('viewGroup', None)
        if viewgroup in self._viewgroups:
            self._child = self._viewgroups[viewgroup]
        self._data.update(element.attrib)
        return element

    def process_element(self, element):
        child = self._child
        if element.tag in self._viewgroups:
            child = self._viewgroups[element.tag]
        key = element.attrib.get('key', None)
        if key:
            url_key = _join_plex(self._url_parts[2], key)
            if url_key in self._keygroups:
                child = self._keygroups[url_key]
        item = child(self, key, element)
        self._items.append(item)
        for index in item.indices:
            self._itemsdict[index] = item

    def get(self, key, default=NO_DEFAULT):
        self.load()
        if key in self._itemsdict:
            return self._itemsdict[key]
        if default is NO_DEFAULT:
            return self._data[key]
        return self._data.get(key, default)
    __getattr__ = __getitem__ = get

    def __dir__(self):
        base = list(super(BaseDirectory, self).__dir__())
        found = list(self._itemsdict.keys())
        data = list(self._data.keys())
        return sorted(list(set(base + found + data)))

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    @property
    def first(self):
        return self.items[0]

    @property
    def items(self):
        self.load()
        return self._items

    @property
    def data(self):
        self.load()
        return self._data

    @property
    def element(self):
        return self._element


class PlexServer(BaseDirectory):
    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, value):
        if not isinstance(value, dict):
            raise TypeError("headers should be a dict")
        self._headers = value

    def add_header(self, header, value):
        self._headers = self._headers or dict(DEFAULT_HEADERS.items())
        if value is None and header in self._headers:
            del self._headers[header]
        else:
            self._headers[header] = value

    def __repr__(self):
        scheme, netloc, path, qs, fragment = self._url_parts
        return "<%s: %s (%s)>" % (self.__class__.__name__, self.friendlyName, netloc)


class Directory(BaseDirectory):
    def __init__(self, base, relative=None, element=None):
        super(Directory, self).__init__(base, relative=relative)
        self._element = element
        self._data.update(element.attrib)
        for child in element.getchildren():
            self.process_sub_element(child)

    art = image_getter('art')
    thumb = image_getter('thumb')

    def process_sub_element(self, element):
        self.process_element(element)

    @property
    def is_search(self):
        return self._data.get('search', None) == "1"

    def search(self, query):
        search_item = [x for x in self.items if x.is_search]
        if not len(search_item):
            return
        item = search_item[0]
        return self.__class__(item, '?query=%s' % query, item.element)
BaseDirectory._default_viewgroup = Directory


class MultiValue(object):
    def get(self, key, default=NO_DEFAULT):
        self.load()
        if key in self._data:
            return self._data[key]
        ret = []
        for item in self._items:
            if key in item.indices:
                ret.append(item)
        default = None if NO_DEFAULT else NO_DEFAULT
        return ret or default
    __getattr__ = __getitem__ = get


class SelfLoading(object):
    def process_root(self, element):
        subtags = element.getchildren()
        if subtags:
            self._items = []
            self._itemsdict = {}
            element = subtags[0]
        return BaseDirectory.process_root(self, element)


@six.python_2_unicode_compatible
class DataNode(MultiValue):
    _viewgroups = {}
    _default_viewgroup = None

    def __init__(self, base, relative=None, element=None):
        self._element = element
        self._items = []
        self._data = {}
        self._data.update(element.attrib)
        self._url_parts = base._url_parts
        for child in element.getchildren():
            self.process_element(child)

    def __repr__(self):
        value = self.value
        if value:
            return "<%s: %s>" % (self.__class__.__name__, self.value.encode('ascii', 'ignore'))
        return "<%s>" % (self.__class__.__name__)

    def load(self):
        pass

    def process_element(self, element):
        child = self._default_viewgroup
        if element.tag in self._viewgroups:
            child = self._viewgroups[element.tag]
        item = child(self, element.attrib.get('key', None), element)
        self._items.append(item)

    def __str__(self):
        return self.value

    @property
    def data(self):
        return self._data

    @property
    def items(self):
        return self._items

    @property
    def element(self):
        return self._element

    @property
    def indices(self):
        return self.get_indices()

    @property
    def value(self):
        return self.get('tag', None)

    def get_indices(self):
        return [self.element.tag]
DataNode._default_viewgroup = DataNode


def register_viewgroup(name):
    def _inner(x):
        BaseDirectory._viewgroups[name] = x
        return x
    return _inner


def register_datanode(name):
    def _inner(x):
        DataNode._viewgroups[name] = x
        return x
    return _inner


def register_keynode(name):
    def _inner(x):
        BaseDirectory._keygroups[name] = x
        return x
    return _inner
