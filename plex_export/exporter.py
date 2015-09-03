from __future__ import unicode_literals, absolute_import, print_function

import os
import argparse
from jinja2 import Environment, FileSystemLoader

from . import PlexServer

try:
    from .version_info import __version__
except ImportError:
    __version__ = '0.0.0'


parser = argparse.ArgumentParser(description='Exports your current library to a template html file.')
parser.add_argument('plexurl', help='Url to your plex server. Optionally add ?X-Plex-Token=<token> if your plex server requires auth.')
parser.add_argument('template', help='Path to the template to parse. The directory of this file will be added to the list of template directories')
parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'))
parser.add_argument('-d', '--dir', action='append', dest='dirname', default=[], help='Add DIRNAME to the list of template directories. Useful when extending or including other templates')
parser.add_argument('-f', '--follow-symlinks', action='store_true', dest='symlinks', help='Tell the template loader to follow symlinks')
parser.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

DEFAULT_EXTENSIONS = [
    'jinja2.ext.loopcontrols',
    'jinja2.ext.with_',
    'jinja2.ext.autoescape',
]


def get_loader(options):
    tpl = options.template
    if '~' in tpl:
        tpl = os.path.expanduser(tpl)
    tpl = os.path.abspath(options.template)
    if not os.path.exists(tpl):
        parser.error("input file '%s' does not exist" % options.template)
    dname, fname = os.path.split(tpl)
    loaders = [dname] + [os.path.abspath(d) for d in options.dirname]
    return FileSystemLoader(loaders, followlinks=options.symlinks), fname


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
    data = {
        'plex': plex,
        'server': plex,
        'library': plex.library,
        'current_server': plex.servers.from_machine_id(plex.machineIdentifier),
        'version': __version__,
    }
    rendered = template.render(**data)
    if options.outfile:
        options.outfile.write(rendered)
        options.outfile.close()
    else:
        print(rendered)
