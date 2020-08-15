"""FilterPatterns.sc"""

from ...base import stream as stm
from ...base import utils as utl
from .. import pattern as ptt


class FilterPattern(ptt.Pattern):
	def __init__(self, pattern):
		self.pattern = pattern


# Pn
# Pgate
# FuncFilterPattern
# Pcollect
# Pselect
# Preject
# Pfset
# Psetpre
# Paddpre
# Pmulpre
# Pset
# Padd
# Pmul
# Psetp
# Paddp
# Pmulp
# Pstretch
# Pstretchp
# Pplayer
# Pdrop


class Pfin(FilterPattern):
    def __init__(self, count, pattern):  # *** No deberían ir al revés?
        self.pattern = pattern
        self.count = count

	# storeArgs

    def __embed__(self, inevent=None):
        stream = stm.stream(self.pattern)
        cleanup = xxx.EventStreamCleanup()
        for _ in utl.counter(self.count):
            try:
                inevent = stream.next(inevent)
            except StopStream:
                return inevent
            cleanup.update(inevent)
            inevent = yield inevent
        return cleanup.exit(inevent)


# And more...
