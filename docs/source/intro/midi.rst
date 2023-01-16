
.. warning:: Under construction.

MIDI Support
============

Installation
------------

MIDI support need some extra dependencies. The main dependencie is mido wich
is installed whith python-rtmidi as default backend. To install the library
with MIDI support use the following command:

::

  pip install sc3[midi]

Or, if sc3 whas already installed without MIDI install mido and python-rtmidi
libraries directly from PyPI.

::

  pip install mido python-rtmidi

The MIDI backend is automatically initialized and uses default mido's
configuration. To configure mido's backend see its
`documentation <https://mido.readthedocs.io/en/latest/backends/index.html>`_.

If using pipewire, e.g. on Fedora, install pipewire's development files
for jack and manually add the linking location before pip install for
python-rtmidi.

::

  sudo dnf install pipewire-jack-audio-connection-kit-devel
  LIBRARY_PATH=/usr/lib64/pipewire-0.3/jack/ pip install python-rtmidi

.. note:

    Change LIBRARY_PATH according to your installation and version.
    If python-rtmidi needs to be compiled other dependecies are also
    needed: gcc-c++, cython, python3-devel, alsa-lib-devel.


Usage
-----

In rt mode, messages can be received or sent through `MidiIn` and `MidiOut`
instances which work seamlessly with MidiFunc and events. To list MIDI ports
available to connect as inputs to the library use the `sources` class method
of `MidiIn`.

::

  MidiIn.sources()

And, for listing MIDI ports available as targets of the library use the
`destination` class method of `MidiOut`.

::

  MidiOut.destinations()

Inputs and outputs can be instantiated in two different ways. To connect a
library input or output to an existing source or destination, objects can
be instantiated with the name listed by the corresponding methods.

::

  src_name = MidiIn.sources()[1]
  mi = MidiIn(src_name)
  dst_name = MidiOut.destinations()[1]
  mo = MidiOut(dst_name)

Receiving MIDI:

::

  from sc3.all import *

  mi = MidiIn('sc3 input 0', True)
  mo = MidiOut(mi.name)

  @midifunc(['note_on', 'note_off'])
  def f(msg, mi):
      print(msg, mi)

  play(type='midi', midiout=mo, midinote=84)
  # {'type': 'note_on', 'time': 0, 'note': 84, 'velocity': 12, 'channel': 0} MidiIn('sc3 input 0', False)
  # {'type': 'note_off', 'time': 0, 'note': 84, 'velocity': 12, 'channel': 0} MidiIn('sc3 input 0', False)

Sending MIDI:

::

  play(type='midi', midiout=mo, midinote=84, velocity=12)

  event(type='midi', midiout=mo, midinote=84).play()

  event({'type': 'midi', 'midiout': mo, 'midinote': 84}).play()

  mo.send_msg('note_on', note=84, velocity=12)
  mo.send_msg('note_off', note=84, velocity=12)


Mido's representation
---------------------

In this library the objects `MidiIn` and `MidiOut` mimic the behavior of
`NetAddr` and `send_msg` for OSC commands but adapted to MIDI messages.

Events and `MidiOut.send_msg` use mido's dictionary based representation which
gets along with SuperCollider's event model. Instead of providing long and
confusing exmplantions about which message's bits does what, mido uses names
for different types of messages and parameters which are fairly easyeasier to
remember and produces more meaningful code.

For events that define midi messages the type key should be set to `'midi'`
and can be used with the `play` function `event` objects. When using
`MidiOut.send_msg` directly the first argument is the event type and its
attributes are passed as keyword arguments as shown in the examples above.

See mido's `documentation <https://mido.readthedocs.io/en/latest/index.html>`_
for more details about message attributes.


MIDI in NRT
-----------

MIDI files can also be created with NRT scripts using the resources of the
library, e.g. routines and patterns.

Script example using routines:

::

  from sc3.all_nrt import *

  mo = MidiOut('channel 1')

  @routine
  def r():
      mo.send_msg('note_on', note=72, velocity=64)
      yield 1
      mo.send_msg('note_off', note=72, velocity=64)
      for i in range(3):
          play(type='midi', midiout=mo, midinote=60 + i, velocity=64, legato=1)
          yield 1

  r.play()

  score = main.process(proto='midi')
  print(score.duration)
  score.write('test.mid')

Script example using patterns:

::

  from sc3.all_nrt import *

  mo = MidiOut('channel 1')

  clock = TempoClock(90/60)

  Pbind({
      'midinote': Pxrand([0, 2, 4, 7, 9, 12], 30) + 60,
      'dur': 0.25,
      'velocity': 64,
      'sustain': 1
  }).play(clock, proto={'type': 'midi', 'midiout': mo})

  score = main.process(proto='midi')
  print(score.duration)
  print(score.list)
  score.write('test.mid')
