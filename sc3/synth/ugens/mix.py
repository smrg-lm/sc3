
import logging

from ...base import utils as utl
from .. import ugen as ugn
from .. import _graphparam as gpp
from . import line as lne


_logger = logging.getLogger(__name__)


class Mix(ugn.PseudoUGen):
    @classmethod
    def new(cls, lst):
        lst = utl.as_list(lst)
        reduced_lst = utl.clump(lst, 4)
        mixed_lst = []
        for item in reduced_lst:
            length = len(item)
            if length == 4:
                mixed_lst.append(ugn.Sum4.new(*item))
            elif length == 3:
                mixed_lst.append(ugn.Sum3.new(*item))
            else:
                mixed_lst.append(utl.list_sum(item))
        if len(mixed_lst) < 3:
            return utl.list_sum(mixed_lst)
        elif len(mixed_lst) == 3:
            return ugn.Sum3.new(*mixed_lst)
        else:
            return cls.new(mixed_lst)

    @classmethod
    def ar(cls, lst):
        result = cls.new(lst)
        rate = result._as_ugen_rate()
        if rate == 'audio':
            return result
        elif rate == 'control':
            return lne.K2A.ar(result)
        elif rate == 'scalar':
            return lne.DC.ar(result)
        else:
            raise ValueError(f'unsupported rate {rate} for Mix.ar')

    @classmethod
    def kr(cls, lst):
        # // 'rate' on an array returns the fastest rate
        # // ('audio' takes precedence over 'control' over 'scalar')
        if gpp.ugen_param(lst)._as_ugen_rate() == 'audio':
            _logger.warning(
                'audio rate input(s) to Mix.kr will '
                'result in signal degradation')
            for i, item in enumerate(lst[:]):
                rate = gpp.ugen_param(item)._as_ugen_rate()
                if rate == 'audio':
                    print(f'{type(item).__name__} {rate}')
                    item._dump_args()
                    lst[i] = lne.A2K.kr(item)
        result = cls.new(lst)
        rate = result._as_ugen_rate()
        if rate == 'control':
            return result
        elif rate == 'scalar':
            return lne.DC.kr(result)
        else:
            raise ValueError(f'unsupported rate {rate} for Mix.kr')


# This is a later added Pseudo UGen used only by JITLib.
# class NumChannels(ugn.PseudoUGen):
#     @classmethod
#     def ar(cls, input, num_channels=2, mixdown=True):
#         input = utl.as_list(input)
#         if len(input) > 1:
#             input = utl.clump(input, bi.ceil(len(input) / num_channels))  # *** BUG: in sclang, will work only if len(input) is >= num_channels AND roundup is multiple of num_channels.
#             result = []
#             for channel in input:
#                 if len(channel) == 1:
#                     result.append(channel[0])
#                 elif mixdown:
#                     result.append(Mix.new(channel))
#                 else:
#                     result.append(channel[0])  # drop the rest
#             if len(result) == 1:
#                 return result[0]
#             else:
#                 return ugn.ChannelList(result)
#         elif num_channels == 1:
#             return input[0]
#         else:
#             return ugn.ChannelList(input * num_channels)  # list dup
