.. _synthdef:

.. warning:: Under construction.

Synthesis definitions
=====================

Synthesis definitions (:term:`synthdefs<synthdef>`) are the
specification of sound synthesis or processing algorithms based
on connecting unit generators (:term:`ugens<ugen>`). The latter
are C/C++ efficient algorithms that perform specific tasks, such
as oscillator, sound capture, playback and so on, they are
pre-compiled as plugins (dynamic libraries) and can't be modified.
However, they can be combined to create higher level signal
processing algorithms that perform more complex tasks and this
is done by creating synthdefs.

When we define a synthdef using the language we are not creating
an object in the server but a blueprint that we will send to the
server that will use it to create synthesis nodes, which are some
kind of higher level unit generators. Synthesis definitions are
also non modifiable once the blueprint is in the server, although
they can be overwritten.

So far, ugens and synthdefs are static elements, in the sense
that they can't be modified once created. On the other hand
synthesis nodes can be created and `patched` dynamically as
discussed below.

A synthdef is created from a Python function definition that
contains interconnected ugen objects. To create the instructions
to be sent to the server (the blueprint) the library analyzes
the tree formed by the ugens and their parameters from an output
ugen, technically any ugen that has side effects, and does some
introspection to the function as we will see later.

The following example show the process of creating and sending
a synthdef.

::

  def sine():
      freq = 440
      amp = 0.1
      sig = SinOsc(freq) * amp
      Out(0, sig)

  sd = SynthDef('sine', sine)
  sd.add()

The ``sine`` function defines the relation between ugens. Then
the function is passed to the ``SynthDef`` object constructor
that receives the name of the synthdef as a string and the
function. Finally the synthdef is sent to the server by calling
its ``add`` method.

The ``sine`` function contains a ``SinOsc`` ugen that receives
a scalar argument, ``freq``, and its output signal is then
multiplied by another scalar, ``amp``, which create a mul ugen,
and the the resulting signal is patched to the output ugen
``Out``. The resulting server instructions can be seen with
the following method:

::

  sd.dump_ugens()


As the example shows, ugens can be interconnected by either
parameters or operations, and also methods that represent
operations. Basically, the valid types to combine with ugens
are numbers, int or float, lists or tuples containing valid
types and other ugens. Some ugens may be able to receive
other object like strings, buses, buffers or special objects
but they will be internally converted to basic types.


Synthesis nodes
---------------


Multichannel expansion
----------------------


Rates
-----
