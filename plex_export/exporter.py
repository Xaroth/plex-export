from __future__ import unicode_literals, absolute_import, print_function

import os
import argparse
from os.path import abspath
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, PackageLoader

from . import PlexServer

try:
    from .version_info import __version__
except ImportError:
    __version__ = '0.0.0'


class KeyValueOption(argparse.Action):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', {})
        kwargs.setdefault('required', False)
        super(KeyValueOption, self).__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        container = getattr(namespace, self.dest, None)
        if container is None:
            container = {}
            setattr(namespace, self.dest, container)
        if '=' not in values:
            parser.error('Options should be specified in the format key=value')
        k, v = values.split('=', 1)
        container[k] = v


parser = argparse.ArgumentParser(description='Exports your current library to a template html file.')
parser.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)
group = parser.add_argument_group("Input/Output")
group.add_argument('plexurl', help='Url to your plex server. Optionally add ?X-Plex-Token=<token> if your plex server requires auth.')
group.add_argument('template', help='Path to the template to parse. The directory of this file will be added to the list of template directories unless --builtin is specified')
group.add_argument('outfile', nargs='?', type=argparse.FileType('w'))
group = parser.add_argument_group("Template configuration")
group.add_argument('-d', '--dir', action='append', dest='dirnames', default=[], help='Add DIRNAMES to the list of template directories. Useful when extending or including other templates. This option can be specified multiple times.')
group.add_argument('-p', '--package', action='append', dest='packages', default=[], help='Add PACKAGES to the list of python packages to search for templates. Please note that the "templates" directory under each package is searched in. This option can be specified multiple times.')
group.add_argument('-f', '--follow-symlinks', action='store_true', dest='symlinks', help='Tell the template loader to follow symlinks')
group.add_argument('--relative', action='store_true', dest='relative', help='Assume that <template> is relative to the built-in template folders')
group.add_argument('--use-builtin-folders', action='store_true', dest='builtin_templates', help='Include the standard built-in folders')
group.add_argument('-o', '--option', action=KeyValueOption, dest='options', help='Define variables to be passed directly to the template in the format key=value. This option can be specified multiple times.')

DEFAULT_EXTENSIONS = [
    'jinja2.ext.loopcontrols',
    'jinja2.ext.with_',
    'jinja2.ext.autoescape',
]


def get_loader(options):
    tpl = options.template
    loaders = []
    if not options.relative:
        if '~' in tpl:
            tpl = os.path.expanduser(tpl)
        tpl = abspath(options.template)
        if not os.path.exists(tpl):
            parser.error("input file '%s' does not exist" % options.template)
        dname, tpl = os.path.split(tpl)
        loaders.append(FileSystemLoader(dname, followlinks=options.symlinks))

    if options.dirnames:
        loaders.append(FileSystemLoader([abspath(path) for path in options.dirnames]))
    if options.packages:
        loaders.append(ChoiceLoader([PackageLoader(package) for package in options.packages]))
    if options.builtin_templates:
        loaders.append(PackageLoader('plex_export'))
    return ChoiceLoader(loaders), tpl


def get_plex(options):
    plex = PlexServer(options.plexurl)
    try:
        plex.load()
    except:
        parser.error("Unable to access plex at %s" % options.plexurl)
    return plex


def export(argv=None):
    options = parser.parse_args(argv) if argv else parser.parse_args()
    loader, templatename = get_loader(options)
    env = Environment(loader=loader, extensions=DEFAULT_EXTENSIONS)
    template = env.get_template(templatename)
    plex = get_plex(options)
    data = options.options
    data.update({
        'plex': plex,
        'server': plex,
        'library': plex.library,
        'current_server': plex.servers.from_machine_id(plex.machineIdentifier),
        'version': __version__,
    })
    rendered = template.render(**data)
    if options.outfile:
        options.outfile.write(rendered)
        options.outfile.close()
    else:
        print(rendered)
