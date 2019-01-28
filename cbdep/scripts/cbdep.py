"""
Dependency Management System
"""

import argparse
import logging
import os
import os.path
import pathlib
import sys
import yaml

from .cache import Cache
from .install import Installer
from .platform_introspection import get_platforms

import cbbuild.cbutil.update_tool_check as update_tool_check


# Set up logging and handler
logger = logging.getLogger('cbdep')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
logger.addHandler(ch)


class Cbdep:
    """

    """

    def __init__(self):
        cachedir = pathlib.Path.home() / ".cbdepcache"
        self.cache = Cache(str(cachedir))

    def do_cache(self, args):
        """
        Cache a URL
        """

        self.cache.get(args.url)

    @staticmethod
    def do_platform(_args):
        """
        Display introspected platform information
        """

        logger.debug("Determining platform...")
        print(get_platforms())

    @staticmethod
    def configpath(args):
        """
        Returns the name of the config file defining the available packages
        """

        yamlfile = args.config_file
        if yamlfile is None:
            if getattr(sys, 'frozen', False):
                # running in a bundle
                mydir = pathlib.Path(sys._MEIPASS)
            else:
                # running live
                mydir = pathlib.Path.home()
            yamlfile = str(mydir / "cbdep.config")

        return yamlfile

    def do_install(self, args):
        """
        Install a package based on a descriptor YAML
        """

        installdir = args.dir
        if installdir is None:
            # QQQ
            installdir = "install"
        installdir = str(pathlib.Path(installdir).resolve())

        installer = Installer.fromYaml(
            self.configpath(args), self.cache, args.platform
        )
        installer.install(args.package, args.version, args.x32, installdir)

    def do_list(self, args):
        """
        List available packages
        """

        with open(self.configpath(args)) as y:
            config = yaml.load(y)
        pkgs = list(config['packages'].keys()) \
            + config['classic-cbdeps']['packages']
        print(
            "Available packages (not all may be available on all platforms):"
        )
        for pkg in sorted(pkgs):
            print(f"  {pkg}")
        print()


def main():
    """
    """

    # PyInstaller binaries get LD_LIBRARY_PATH set for them, and that
    # can have unwanted side-effects for our own subprocesses. Remove
    # that here - it can still be set by an env: entry in cbdep.config
    # for an install directive.
    # This needs to be done very early - even the call to get_platforms()
    # below indirectly shells out to lsb_release.
    os.environ.pop("LD_LIBRARY_PATH", None)

    parser = argparse.ArgumentParser(
        description='Dependency Management System'
    )
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debugging output')
    parser.add_argument('-p', '--platform', type=str,
                        default=get_platforms(),
                        help="Override detected platform")
    subparsers = parser.add_subparsers()

    cache_parser = subparsers.add_parser(
        "cache", help="Add downloaded URL to local cache"
    )
    cache_parser.add_argument("url", type=str, help="URL to cache")
    cache_parser.set_defaults(func=Cbdep.do_cache)

    install_parser = subparsers.add_parser(
        "install", help="Install a package"
    )
    install_parser.add_argument("package", type=str,
                                help="Package to install")
    install_parser.add_argument("version", type=str,
                                help="Version to install")
    install_parser.add_argument(
        '-3', '--x32', action="store_true",
        help="Download 32-bit package (default false; only works on "
             "a few packages)"
    )
    install_parser.add_argument("-c", "--config-file", type=str,
                                help="YAML file descriptor")
    install_parser.add_argument(
        "-d", "--dir", type=str,
        help="Directory to unpack into (not applicable for all packages)"
    )
    install_parser.set_defaults(func=Cbdep.do_install)

    platform_parser = subparsers.add_parser(
        "platform", help="Dump introspected platform information"
    )
    platform_parser.set_defaults(func=Cbdep.do_platform)

    list_parser = subparsers.add_parser(
        "list", help="List available cbdep packages"
    )
    list_parser.add_argument("-c", "--config-file",
        type=str, help="YAML file descriptor")
    list_parser.set_defaults(func=Cbdep.do_list)

    args = parser.parse_args()

    tool_name = os.path.basename(sys.argv[0])
    update_tool_check.check_for_update(tool_name, args)

    # Set logging to debug level on stream handler if --debug was set
    if args.debug:
        ch.setLevel(logging.DEBUG)

    # Check that a command was specified
    if "func" not in args:
        parser.print_help()
        sys.exit(1)

    cbdep = Cbdep()
    args.func(cbdep, args)


if __name__ == '__main__':
    main()
