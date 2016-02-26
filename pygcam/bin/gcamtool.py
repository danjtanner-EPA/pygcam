#!/usr/bin/env python2

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
from pygcam.config import DEFAULT_SECTION
import pygcam.query

VERSION = '0.1'

class SubCommand(object):
    """
    Abstract base class for sub-commands. Defines the protocol expected by gcamtool
    for defining sub-commands.
    """
    Instances = {}

    @classmethod
    def getInstance(cls, name):
        return cls.Instances[name]

    def __init__(self, name, kwargs, subparsers):
        self.name   = name      # these must be set in subclass before calling super()
        self.parser = subparsers.add_parser(name, **kwargs)
        self.Instances[name] = self.parser
        self.addArgs()

    def addArgs(self):
        pass

    def run(self, args):
        """
        This is the function invoked by this SubCommand instance.

        :param args: the argument dictionary
        :return: nothing
        """
        pass


class SetupCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(SetupCommand, self).__init__('setup', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass


class GcamCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(GcamCommand, self).__init__('gcam', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass


class QueryCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'fromfile_prefix_chars' : '@',      # use "@" before value to substitute contents of file as arguments

                       'help' : '''Run one or more GCAM database queries by generating and running the
                       named XML queries. The results are placed in a file in the specified
                       output directory with a name composed of the basename of the
                       XML query file plus the scenario name. For example,
                       "gcamtool query -o. -s MyReference,MyPolicyCase liquids-by-region"
                       would generate query results into the files ./liquids-by-region-MyReference.csv
                       and ./liquids-by-region-MyPolicyCase.csv.

                       The named queries are located using the value of config variable GCAM.QueryPath,
                       which can be overridden with the -Q argument. The QueryPath consists of one or
                       more colon-delimited elements that can identify directories or XML files. The
                       elements of QueryPath are searched in order until the named query is found. If
                       a path element is a directory, the filename composed of the query + '.xml' is
                       sought in that directory. If the path element is an XML file, a query with a
                       title matching the query name (first literally, then by replacing '_' and '-'
                       characters with spaces) is sought. Note that query names are case-sensitive.

                       This script populates an initial configuration file in ~/.pygcam.cfg when
                       first run. The config file should be customized as needed, e.g., to set "GcamRoot"
                       to the directory holding your Main_User_Workspace unless it happens to live in
                       ~/GCAM, which is the default value.'''}

        super(QueryCommand, self).__init__('query', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('queryName', type=str, nargs='*',
                            help='''A file or files, each holding an XML query to run. (The ".xml" suffix will be added if needed.)
                                    If an argument is preceded by the "@" sign, it is read and its contents substituted as the
                                    values for this argument. That means you can store queries to run in a file (one per line) and
                                    just reference the file by preceding the filename argument with "@".''')

        parser.add_argument('-c', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-d', '--xmldb', type=str,
                             help='''The XML database to query (default is value of GCAM.DbFile, in the GCAM.Workspace's
                             "output" directory. Overrides the -w flag.''')

        parser.add_argument('-D', '--dontDelete', action="store_true",
                            help='''Don't delete any temporary file created by extracting a query from a query file. Used
                                    mainly for debugging.''')

        parser.add_argument('-R', '--regionMap', type=str,
                            help='''A file containing tab-separated pairs of names, the first being a GCAM region
                                    and the second being the name to map this region to. Lines starting with "#" are
                                    treated as comments. Lines without a tab character are also ignored. This arg
                                    overrides the value of config variable GCAM.RegionMapFile.''')

        parser.add_argument('-n', '--noRun', action="store_true",
                            help="Show the command to be run, but don't run it")

        parser.add_argument('-o', '--outputDir', type=str,
                             help='Where to output the result (default taken from config parameter "GCAM.OutputDir")')

        parser.add_argument('-Q', '--queryPath', type=str, default=None,
                            help='''A colon-delimited list of directories or filenames to look in to find query files.
                                    Defaults to value of config parameter GCAM.QueryPath''')

        parser.add_argument('-r', '--regions', type=str, default=None,
                            help='''A comma-separated list of regions on which to run queries found in query files structured
                                    like Main_Queries.xml. If not specified, defaults to querying all 32 regions.''')

        parser.add_argument('-s', '--scenario', type=str, default='Reference',
                            help='''A comma-separated list of scenarios to run the query/queries for (default is "Reference")
                                    Note that these refer to a scenarios in the XML database.''')

        parser.add_argument('-v', '--verbose', action='count',
                            help="Show command being executed.")

        parser.add_argument('-w', '--workspace', type=str, default='',
                            help='''The workspace directory in which to find the XML database.
                                    Defaults to value of config file parameter GCAM.Workspace.
                                    Overridden by the -d flag.''')

    def run(self, args):
        pygcam.query.main(args)


class DiffCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(DiffCommand, self).__init__('diff', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass


class ChartCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(ChartCommand, self).__init__('chart', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass

class ProjectCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(ProjectCommand, self).__init__('project', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass

class ProtectCommand(SubCommand):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(ProtectCommand self).__init__('protect', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass


SubCommandClasses = [SetupCommand, GcamCommand, QueryCommand, DiffCommand,
                     ChartCommand, ProjectCommand, ProtectCommand]

class GcamTool(object):

    def __init__(self):
        self.parser = None
        self.subparsers = None  # set by setupMainParser()

        self.setupMainParser()

        # Add all the known SubCommand classes
        for cls in SubCommandClasses:
            cls(self.subparsers)

    def setupMainParser(self):
        self.parser = argparse.ArgumentParser()
        parser = self.parser

        # Note that the "main_" prefix is significant; see _is_main_arg() above
        # parser.add_argument('-V', '--main_verbose', action='store_true', default=False,
        #                     help='Causes log messages to be printed to console.')

        parser.add_argument('-L', '--log_level', default=None,
                            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
                            help='Sets the log level of the program.')

        parser.add_argument('--version', action='version', version=VERSION)

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                                                     description='''For help on subcommands, use the "-h"
                                                                    flag after the subcommand name''')

    def run(self):
        """
        Parse the script's arguments and invoke the run() method of the
        designated sub-command.

        :return: none
        """
        args = self.parser.parse_args()
        cmd = args.subcommand

        # Remove so sub-command doesn't see this
        del args.subcommand

        # Run the sub-command
        obj = SubCommand.getInstance(cmd)
        obj.run(args)


if __name__ == '__main__':
    GcamTool().run()