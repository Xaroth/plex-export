from __future__ import unicode_literals, absolute_import
from .base import register_datanode, register_viewgroup, register_keynode, SelfLoading, MultiValue, Directory, DataNode, image_getter

import six


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
class DirectorItem(RoleItem):
    pass


@register_viewgroup('Writer')
class WriterItem(RoleItem):
    pass


@register_viewgroup('Producer')
class ProducerItem(RoleItem):
    pass


@register_viewgroup('Collection')
class CollectionItem(DataNode):
    pass


@register_viewgroup('Server')
class ServerItem(DataNode):
    @property
    def value(self):
        return self.name


@register_keynode('servers/')
class ServerListing(Directory):
    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        if isinstance(index, six.integer_types):
            return self.items[index]
        elif isinstance(index, six.string_types):
            for item in self.items:
                if item.name == index:
                    return item
        raise IndexError(index)

    def from_machine_id(self, machine_id):
        for item in self.items:
            if item.machineIdentifier == machine_id:
                return item
        return None
