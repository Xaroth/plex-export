from __future__ import unicode_literals, absolute_import
from .base import register_datanode, register_viewgroup, SelfLoading, MultiValue, Directory, DataNode, image_getter


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
    
