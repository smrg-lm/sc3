"""NodeWatcher.sc"""

from ..base import responsedefs as rdf
from ..base import systemactions as sac


# //watches a server address for node-related messages

class AbstractNodeWatcher():
    ...


class BasicNodeWatcher(AbstractNodeWatcher):
    ...


# // Watches registered nodes and sets their isPlaying/isRunning flag.
# // A node needs to be registered to be addressed, other nodes are ignored.
class NodeWatcher(BasicNodeWatcher):
    ...


class DebugNodeWatcher(BasicNodeWatcher):
    ...
