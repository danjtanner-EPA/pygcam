from pygcam.plugin import PluginBase

class ChartCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(ChartCommand, self).__init__('chart', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass

PluginClass = ChartCommand
