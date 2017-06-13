from .addexp_plugin import AddExpCommand
from .analyze_plugin import AnalyzeCommand
from .cluster_plugin import ClusterCommand
from .delsim_plugin import DelSimCommand
from .discrete_plugin import DiscreteCommand
from .engine_plugin import EngineCommand
from .gensim_plugin import GensimCommand
from .iterate_plugin import IterateCommand
from .newsim_plugin import NewSimCommand
from .parallelPlot_plugin import ParallelPlotCommand
from .runsim_plugin import RunSimCommand

MCSBuiltins = [AddExpCommand, AnalyzeCommand, ClusterCommand,
               DiscreteCommand, GensimCommand, DelSimCommand,
               EngineCommand, IterateCommand, NewSimCommand,
               ParallelPlotCommand, RunSimCommand]