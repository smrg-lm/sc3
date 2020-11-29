"""Global play shortcut mostly for events and lambdas."""

import logging
import inspect

from . import utils as utl
from . import responsedefs as rdf
from ..seq import event as evt
from ..synth import synthdef as sdf
from ..synth import _graphparam as gpp
from ..synth import ugen as ugn
from ..synth import ugens as ugns
from ..synth import envelope as evp
from ..synth import systemdefs as sds
from ..synth import node as nod
from ..synth import buffer as bff


__all__ = ['play']


_logger = logging.getLogger(__name__)


def _play_func(func, target=None, outbus=0, fade=0.01,
               add_action='addToHead', args=()):
    # asDefName.sc
    target = gpp.node_param(target)._as_target()
    server = target.server
    if not server._status_watcher.server_running:
        _logger.warning(f'server {str(server.name)} not running')
        return

    # GraphBuilder.sc
    def wrapper(_iout:'ir'=0):
        # SynthDef.wrap function has to return an UGen-input or
        # None to be chained or not. UGens that don't return a
        # signal should return None. Generated synthdef of this
        # version of func.play() differs a bit from the original.
        result = sdf.SynthDef.wrap(func)
        if result is not None:
            if fade:
                ugns.Control.add_name('gate')
                gate = ugns.Control.kr(1.0)
                result *= ugns.EnvGen.kr(
                    evp.Env.asr(fade, 1, fade, 'lin'), gate, 1, 0, 1, 2)
            result = ugn.SynthObject._replace_zeroes_with_silence(
                utl.as_list(result))
            rate = gpp.ugen_param(result)._as_ugen_rate()
            ugns.Out._multi_new(rate, _iout, *result)

    synthdef = sdf.SynthDef(sds.SystemDefs.generate_tmp_name(), wrapper)
    synth = nod.Synth.basic_new(synthdef.name, server)
    rdf.OscFunc(
        # // Use the /n_end signal to remove the temp synthdef.
        lambda *_: server.send_msg('/d_free', synthdef.name),
        '/n_end', server.addr, arg_template=[synth.node_id]).one_shot()
    args = gpp.node_param(args)._as_control_input()
    synth_msg = synth.new_msg(
        target, ['_iout', outbus, 'out', outbus, *args], add_action)
    synthdef._do_send(server, synth_msg)
    return synth


def _play_buf(buf, loop=False, mul=1, **kwargs):
    if buf._bufnum is None:
        raise bff.BufferAlreadyFreed('_play_buf')

    def buffer_player():
        sig = ugns.PlayBuf.ar(
            buf._channels, buf._bufnum,
            ugns.BufRateScale.kr(buf._bufnum), loop=loop)
        if not loop:
            ugns.FreeSelfWhenDone.kr(sig)
        return sig * mul

    return _play_func(buffer_player, buf._server, **kwargs)


def play(obj=None, *args, **kwargs):
    '''Convenience function to play events and lambdas.

    If called without any argument it will play the default event
    with the default parameters.

    If called only with keyword arguments create an event with
    those keys and plays it.

    If ``obj`` defines the method ``play`` just calls it with
    `*args` and `**kwargs`.

    If ``obj`` is a dict, it creates an event and plays it adding
    kwargs if any. Only keyword arguments are allowed for this case.

    If ``obj`` is a function, it creates a temp SynthDef and makes a
    Synth from it. The function should return the expression to be
    played or have it's own output. This is mostly intended for simple
    lambda functions but can be used as a decorator.

    All versions return the return value of the played object.
    '''

    if not obj and not args and not kwargs:
        # Test tone.
        return evt.event().play()  # TODO: Event is not returning the created server object.
    elif hasattr(obj, 'play'):
        # Is playable.
        return obj.play(*args, **kwargs)
    elif isinstance(obj, dict) and not args:
        # As event.
        return evt.event({**obj, **kwargs}).play()
    elif inspect.isfunction(obj):
        # Decorator or play(lmbd, s, 0, ...).
        return _play_func(obj, *args, **kwargs)
    elif isinstance(obj, bff.Buffer):
        return _play_buf(obj, *args, **kwargs)
    elif obj is None and not args and kwargs:
        # As a keyword only call makes an event.
        return evt.event(kwargs).play()
    else:
        raise ValueError(f'non playable arguments')
