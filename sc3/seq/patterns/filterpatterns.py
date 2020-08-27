"""FilterPatterns.sc"""

import copy

from ...base import builtins as bi
from ...base import stream as stm
from ...base import utils as utl
from ...base import functions as fn
from .. import pattern as ptt


utl.ClassLibrary.late_imports(__name__, ('sc3.seq.pausestream', 'pst'))


class FilterPattern(ptt.Pattern):
	def __init__(self, pattern):
		self.pattern = pattern


class Pn(FilterPattern):
	def __init__(self, pattern, repeats=bi.inf, key=None):
		self.pattern = pattern
		self.repeats = repeats
		self.key = key

	def __stream__(self):
		return pst.PatternEventStream(self)

	def __embed__(self, inevent):
		pattern = self.pattern
		key = self.key
		if key is None:
			for _ in utl.counter(self.repeats):
				inevent = yield from pattern.__embed__(inevent)
		else:
			for _ in utl.counter(self.repeats):
				inevent[key] = True
				inevent = yield from pattern.__embed__(inevent)
			inevent[key] = False
		return inevent

	# storeArgs


class Pgate(Pn):
	def __embed__(self, inevent):
		pattern = self.pattern
		key = self.key
		stream = output = None
		for _ in utl.counter(self.repeats):
			stream = stm.stream(pattern)
			try:
				while True:
					if inevent.get(key, False) is True or output is None:
						output = stream.next(inevent)
					inevent = yield from stm.embed(copy.copy(output), inevent)
			except stm.StopStream:
				pass
			output = None   # // Force new value for every repeat.
		return inevent

	# storeArgs


class FuncFilterPattern(FilterPattern):
	def __init__(self, func, pattern):
		super().__init__(pattern)
		self.func = func


class Pcollect(FuncFilterPattern):
	def __embed__(self, inval):
		fun = self.func
		pstream = stm.stream(self.pattern)
		inval = outval = None
		try:
			while True:
				outval = pstream.next(inval)
				inval = yield fn.value(func, outval, inval)
		except stm.StopStream:
			return inval


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

    def __embed__(self, inevent):
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
