from __future__ import unicode_literals, absolute_import

import requests
import six
from six.moves.urllib import parse

from .. import exceptions

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET
NO_DEFAULT = object()


def _join_plex(x, y):
    url = parse.urljoin(x, y)
    if not url.endswith('/'):
        url = url + '/'
    return url


class RequestBase(object):
    def __init__(self, base, relative=None):
        self._has_token = False
        self._url = None
        self._url_parts = None
        self._loaded = False
        self._xml = None
        self._url_parts = None
        if isinstance(base, six.string_types):
            base_url = base
            self._url_parts = list(parse.urlsplit(base_url))
        elif isinstance(base, RequestBase):
            base_url = base.url
            self._has_token = base.has_token
            self._url_parts = base._url_parts[:]
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

    def __repr__(self):
        scheme, netloc, path, qs, fragment = self._url_parts
        return "<%s: %s%s>" % (self.__class__.__name__, netloc, path)

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
    viewgroups = {}
    default_viewgroup = None

    def __init__(self, base, relative=None):
        self._items = []
        self._itemsdict = {}
        self._child = self.default_viewgroup
        self._data = {}
        super(BaseDirectory, self).__init__(base, relative=relative)

    @property
    def indices(self):
        keys = ['key', 'type', 'title']
        bad_tokens = lambda x: '/' in x or '?' in x
        return [x for x in [self._data.get(key, None) for key in keys] if x and not bad_tokens(x)]

    def process_root(self, element):
        viewgroup = element.attrib.get('viewGroup', None)
        if viewgroup in self.viewgroups:
            self._child = self.viewgroups[viewgroup]
        self._data.update(element.attrib)
        return element

    def process_element(self, element):
        child = self._child
        if element.tag in self.viewgroups:
            child = self.viewgroups[element.tag]
        item = child(self, element.attrib.get('key', None), element)
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

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

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
BaseDirectory.default_viewgroup = Directory


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
        subtag = element.xpath('//MediaContainer/*[1]')
        if subtag:
            self._items = []
            self._itemsdict = {}
            element = subtag[0]
        return BaseDirectory.process_root(self, element)


class DataNode(MultiValue):
    viewgroups = {}
    default_viewgroup = None

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
        child = self.default_viewgroup
        if element.tag in self.viewgroups:
            child = self.viewgroups[element.tag]
        item = child(self, element.attrib.get('key', None), element)
        self._items.append(item)

    # def get(self, key, default=NO_DEFAULT):
    #     if default is NO_DEFAULT:
    #         return self._data[key]
    #     return self._data.get(key, default)
    # __getattr__ = __getitem__ = get

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
DataNode.default_viewgroup = DataNode


def register_viewgroup(name):
    def _inner(x):
        BaseDirectory.viewgroups[name] = x
        return x
    return _inner


def register_datanode(name):
    def _inner(x):
        DataNode.viewgroups[name] = x
        return x
    return _inner
