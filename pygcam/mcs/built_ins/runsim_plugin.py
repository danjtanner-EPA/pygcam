# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from __future__ import print_function
import argparse
from six import iteritems
from pygcam.error import PygcamException
from pygcam.log import getLogger
from pygcam.subcommand import SubcommandABC

_logger = getLogger(__name__)

def driver(args, tool):
    from ipyparallel import NoEnginesRegistered
    from ..master import Master, pidFileExists, startCluster

    if args.startCluster:
        # If the pid file doesn't exist, we assume the cluster is
        # not running and we run it with the given profile and
        # cluster ID, relying on the config file for other parameters.
        # To specify other params, use "gt cluster start" instead.
        if pidFileExists(args.profile, args.clusterId):
            _logger.warning('ipyparallel cluster is (probably) already running')
        else:
            _logger.info('Starting ipyparallel cluster')
            kwargs = {key : getattr(args, key, None) \
                      for key in ('profile', 'clusterId', 'numTrials',
                                  'maxEngines', 'minutesPerRun', 'queue')}
            startCluster(**kwargs)

    master = Master(args)
    try:
        master.processTrials(loopOnly=args.loopOnly, addTrials=args.addTrials)
    except NoEnginesRegistered as e:
        raise PygcamException("processTrials aborted: %s" % e)

#
# Custom argparse "action" to parse comma-delimited strings to lists
# TBD: move this to central location and use it where relevant
#
class ParseCommaList(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed with " % option_strings)

        super(ParseCommaList, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))


class RunSimCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''(MCS) Run the identified trials on compute engines.'''}
        super(RunSimCommand, self).__init__('runsim', subparsers, kwargs)

    def addArgs(self, parser):
        from pygcam.config import getParam, getParamAsInt, getParamAsFloat

        # deprecated
        # defaultMinutes   = getParamAsFloat('IPP.MinutesPerRun')

        defaultProfile    = getParam('IPP.Profile')
        defaultClusterId  = getParam('IPP.ClusterId')
        defaultQueue      = getParam('IPP.Queue')
        defaultMaxEngines = getParamAsInt('IPP.MaxEngines')
        defaultMinutes    = getParamAsFloat('IPP.MinutesPerRun')
        defaultWaitSecs   = getParamAsFloat('IPP.ResultLoopWaitSecs')

        # TBD: document this variable
        defaultScenario = getParam('MCS.DefaultScenario', raiseError=False)
        scenarioHelp = 'Default value is "%s".' % defaultScenario \
                            if defaultScenario else "No default has been set."

        parser.add_argument('-a', '--addTrials', action='store_true',
                            help='''Add trials to a running cluster; don't wait for results.''')

        parser.add_argument('-B', '--noBatchQueries', action='store_true',
                            help='Skip running batch queries.')

        parser.add_argument('-c', '--clusterId', type=str, default=defaultClusterId,
                            help='''A string to identify this cluster. Default is the
                            value of config var IPP.ClusterId, currently
                            "%s".''' % defaultClusterId)

        parser.add_argument('-C', '--startCluster', action='store_true',
                            help='''Start the cluster, if not already running, using the given
                            profile name and cluster ID with other parameters taken from the
                            config file. To start a cluster with other parameters, see run the
                            "gt cluster start" command before running runsim.''')

        parser.add_argument('-D', '--noDatabase', dest='updateDatabase', action='store_false',
                            help='''Don't save query results to the SQL database.''')

        parser.add_argument('-e', '--maxEngines', type=int, default=defaultMaxEngines,
                            help='''Set maximum number of engines to create. (Ignored 
                            unless -C flag is specified.
                            Overrides config parameter IPP.MaxEngines, currently
                            %s''' % defaultMaxEngines)

        parser.add_argument('-g', '--groupName', default='',
                            help='''The name of a scenario group to process.''')

        parser.add_argument('-G', '--noGCAM', action="store_true",
                            help="Don't run GCAM, just run the batch queries and "
                                 "post-processor (if defined).")

        parser.add_argument('-i', '--shutdownWhenIdle', action='store_true',
                            help='''Shutdown engines when they are idle and there are no
                            outstanding tasks, and shutdown controller when there are no
                            engines running.''')

        parser.add_argument('-l', '--runLocal', action='store_true',
                            help='''Runs the program locally instead of submitting a batch job.''')

        parser.add_argument('-L', '--loopOnly', action='store_true',
                            help='''Don't run any new trials; just enter the wait loop to 
                            process results.''')

        parser.add_argument('-m', '--minutesPerRun', type=int, default=defaultMinutes,
                            help='''Set the number of minutes of walltime to allocate
                            per GCAM run. Ignored unless -C flag is specified. Overrides 
                            config parameter IPP.MinutesPerRun, currently %s.''' % defaultMinutes)

        parser.add_argument('-n', '--numTrials', type=int, default=10,
                            help='''The total number of GCAM trials that will be run on this
                            cluster. (Relevant only if starting the cluster via the -C flag.)''')

        parser.add_argument('-N', '--noPostProcessor', action='store_true', default=False,
                            help='''Don't run post-processor steps.''')

        parser.add_argument('-p', '--profile', type=str, default=defaultProfile,
                            help='''The name of the ipython profile to use. Default is
                            the value of config var IPP.Profile, currently
                            "%s".''' % defaultProfile)

        # If alternative flags are added, the hack in run() must be updated
        parser.add_argument('--programArgs', type=str, default=getParam('MCS.ProgramArgs'),
                            help='''Arguments to pass to user program. Quote sequences that include 
                            spaces, e.g., to pass args: -x foo, use --programArgs="-x foo"''')

        parser.add_argument('-q', '--queue', type=str, default=defaultQueue,
                            help='''The queue or partition on which to create the controller
                            and engines. Ignored unless -C flag is used. 
                            Overrides config var IPP.Queue, currently
                            "%s".''' % defaultQueue)

        parser.add_argument('-r', '--redo', dest='statuses', type=str, action=ParseCommaList,
                            help='''Re-launch all trials for the given simId with the status 
                            specified. Argument can be comma-delimited list of status names. When 
                            used with -R, trial numbers are listed but trials are not run.''')

        parser.add_argument('-R', '--redoListOnly', action='store_true', default=False,
                            help='Used with -r to only list the trials to redo, then quit.')

        parser.add_argument('-s', '--simId', type=int, default=1,
                            help='The id of the simulation (Defaults to 1.)')

        parser.add_argument('-S', '--scenario', dest='scenarios', type=str, action=ParseCommaList,
                            # required if no default is set; otherwise use default if not specified
                            required=(not defaultScenario), default=defaultScenario,
                            help='''The name of the scenario(s). May be a comma-separated list of 
                            names. Use config var MCS.DefaultScenario to set a default scenario 
                            name. ''' + scenarioHelp)

        parser.add_argument('-t', '--trials', type=str, default='',
                             help='''Comma-separated list of trial numbers and/or hyphen-separated 
                             ranges of trial numbers to run. Ex: 1,4,6-10,3. Default is to run all 
                             defined trials.''')

        parser.add_argument('-w', '--waitSecs', type=int, default=defaultWaitSecs,
                            help='''How many seconds to wait between queries to the ipyparallel
                            controller for completed jobs. Default is %d.''' % defaultWaitSecs)

        return parser   # for auto-doc generation


    def run(self, args, tool):
        if args.statuses:
            from ..Database import RUN_STATUSES
            from pygcam.error import CommandlineError

            statusSet = set(args.statuses)
            known = set(RUN_STATUSES)
            unknown = statusSet - known
            if unknown:
                raise CommandlineError("Unknown status code(s): %s" % ', '.join(map(repr, unknown)))

        driver(args, tool)

#
# Test stuff
#
if __name__ == '__main__':
    import ipyparallel as ipp
    import time

    clusterId = 'mcs'
    profile = 'pygcam'

    client = ipp.Client(profile=profile, cluster_id=clusterId)
    dview = client[:]
    dview.execute('import time')

    def f(id, secs):
        from ipyparallel.engine.datapub import publish_data
        import time

        publish_data({id : 'running'})
        time.sleep(secs)
        publish_data({id : 'finished'})
        return secs

    def runStatus(res, statuses=None):
        statuses = statuses or {}

        for r in res:
            dataDict = r.data[0]
            if dataDict:
                for id, status in iteritems(dataDict):
                    statuses[id] = status
        return statuses

    def running(res, statuses=None):
        statuses = statuses or {}
        statuses = runStatus(res, statuses)
        return [id for id, status in iteritems(statuses) if status == 'running']

    dview['f'] = f

    lbview = client.load_balanced_view()
    res = [lbview.map_async(f, [i], [20]) for i in range(10)]
    m = res[0].metadata
    # md = res.metadata
    # m  = md[0]
    # kids = res._children
    # kid  = kids[0]
    status = dview.queue_status()
    print(status)

