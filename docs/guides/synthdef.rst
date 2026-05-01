.. _synthdef:

.. warning:: Under construction.

Synthesis definitions
=====================

Synthesis definitions (:term:`synthdefs<synthdef>`) are the specification of
sound synthesis or processing algorithms based on connecting unit generators
(:term:`ugens<ugen>`). The latter are C/C++ efficient algorithms that perform
specific tasks, such as oscillator, sound capture, playback and so on, they are
pre-compiled as plugins (dynamic libraries) and can't be modified. However,
they can be combined to create higher level signal processing algorithms that
perform more complex tasks and this is done by creating synthdefs.

When a synthdef is defined using the language no object is created in the
server but a blueprint with the instructions to create that object that will be
sent to the server which in turn will use it to create synthesis nodes.
Synthesis nodes can be seen as some kind of higher level sound generators
instances. Synthesis definitions are also non modifiable once the blueprint is
in the server, although they can be overwritten.

So far, ugens and synthdefs are static elements, in the sense that they can't
be modified once created. On the other hand synthesis nodes can be created and
`patched` dynamically as discussed below.

A synthdef is created from a Python function definition that contains
interconnected ugen objects. To create the instructions to be sent to the
server (the blueprint) the library analyzes the tree formed by the ugens and
their parameters from an output ugen, technically any ugen that has side
effects, and does some introspection to the function as we will see later.

The following example show the process of creating and sending a synthdef.

::

  def sine():
      freq = 440
      amp = 0.1
      sig = SinOsc(freq) * amp
      Out(0, sig)

  sd = SynthDef('sine', sine)
  sd.add()

The ``sine`` function defines the relations between ugens. Then the function is
passed to the :class:`SynthDef<sc3.synth.synthdef.SynthDef>` object constructor
that receives the name of the synthdef as a string and the function. Finally
the synthdef is sent to the server by calling its ``add`` method.

The ``sine`` function contains a
:class:`SinOsc<sc3.synth.ugens.oscillators.SinOsc>` ugen that receives a scalar
argument, ``freq``, and its output signal is then multiplied by another scalar,
``amp``, which creates a ``*`` ugen, and the the resulting signal is patched to
the output ugen :class:`Out<sc3.synth.ugens.inout.Out>`. The resulting server
instructions can be seen with the following method:

::

  sd.dump_ugens()

Prints:

::

  sine
  ['0_SinOsc', 'audio', [440, 0.0]]
  ['1_*', 'audio', ['0_SinOsc', 0.1]]
  ['2_Out', 'audio', [0, '1_*']]

As the example shows, ugens can be interconnected by either parameters or
operations, and also methods that represent operations. Basically, the valid
types to combine with ugens are numbers, int or float, lists or tuples
containing valid types and other ugens. Some ugens may be able to receive other
special objects but they will be internally converted to basic types.

Synthesis definitions can also be written using the decorator function
:meth:`synthdef<sc3.synth.synthdef.synthdef>` which creates the
:class:`SynthDef<sc3.synth.synthdef.SynthDef>` instance with the name of the
function and adds it to the default running server or at the next boot.

::

  @synthdef
  def mydef():
      ...


Synthesis nodes
---------------

:class:`SynthDef<sc3.synth.synthdef.SynthDef>` objects implements the callable
interface to simplify node creation without sacrificing functionality. In
sc3 it is possible to create a synthesis definition and node as follows:

::

  @synthdef
  def sine(freq=440, amp=0.1, pan=0, gate=1):
      sig = SinOsc(freq) * amp
      env = EnvGen(Env.asr(), gate)
      FreeSelfWhenDone(env)
      Out(0, Pan2(sig * env, pan))

  x = sine(220, pan=-0.5)
  x.release()

The :class:`SynthDef<sc3.synth.synthdef.SynthDef>` object represents the
composed synthesis function and accept positional or keyword arguments as
defined by the graph (``sine``) function. This interface also sends the message
in a bundle so it can be used within routines and keep perfect timing.

In addition to the arguments of the function it is also possible to pass the
parameters of :class:`Synth<sc3.synth.node.Synth>`, ``target``, ``add_action``
and ``register``. For example:

::

  g = Group()
  x = sine(target=g, add_action='tail')


Multichannel expansion
----------------------

List perform multichannel expansion as usual:

::

  x = play(lambda: SinOsc([220, 330, 660]).sum() * 0.01)
  x.free()

Tuples, as basic Python's data structures, have a special meaning when used to
construct synthdefs, they define lists of values as a single value to prevent
multichannel expansion when necessary. For example, to specify vector
arguments.

::

  @synthdef
  def multi(freq=(220, 330, 550), amp=0.1):
      sig = SinOsc(freq) * [0.25, 0.5, 0.3] * amp
      Out(0, Mix(sig).dup())

  x = multi()
  x.set('freq', [110, 111, 112])
  x.free()


Rates
-----

:class:`SynthDef<sc3.synth.SynthDef>` parameters rate is implemented as type
annotations. Annotating the parameter with the strings ``'ar'``, ``'kr'``,
``'ir'`` or ``'tr'`` will create the appropriate rate for control ugens.
Numbers, as annotation, will create lag controls. It is also possible directly
use the class instead of the decorator with all original parameters.

::

  @synthdef
  def sine(out=0, freq=440, amp=0.1, trig:'tr'=1):
      sig = SinOsc(freq) * amp
      env = EnvGen(Env.perc(0.02, 2), trig)
      Out(out, sig * env)

  @synthdef
  def cheaptrem(sig:'ar'=0, freq:'ir'=4, amp:'kr'=1):
      sig = In(sig)
      ctl_pan = SinOsc.kr(freq)
      ctl_amp = ctl_pan.range(0, 1) * amp
      Out(0, Pan2(sig * ctl_amp, ctl_pan))

  g = Group()
  b = AudioBus()

  fx = cheaptrem(b, target=g)
  x = sine(b, target=g, add_action='head')

  x.set('trig', 1)
  x.set('trig', 1)

  x.free()
  fx.free()
