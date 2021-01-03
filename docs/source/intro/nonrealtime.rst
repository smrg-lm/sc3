.. _nonrealtime:

.. warning:: Under construction.

Non real time mode
==================

The library can also run in non real time (NRT) mode. This mode is based on the
`NRTClock` :term:`quark`, with the addition that the whole library timing is
managed in NRT.

In NRT, clocks, routines and random generators work with the same interface as
real time. It was made so code can be easily adapted or run in both modes
without changes.

.. note::

  It's not possible to run the library in both RT and NRT at the same time
  because clocks and :term:`elapsed time` are internally managed in different
  ways. To run a NRT script from a RT library instance could be done by
  creating a sub-process that starts a new interpreter.

The following example can be run as command line script:

::

  #!/usr/bin/env python3

  # Init NRT mode and import all.
  from sc3.all_nrt import *

  # Load default synthdef.
  SystemDefs.add_synthdef('default')

  @routine
  def r1():
      for n in [58, 62, 64, 69, 60, 66, 73]:
          play(midinote=n, sustain=2)
          yield 1

  r1.play(TempoClock(3))

  # Generate the OSC score.
  score = main.process(2)
  # Elapsed time is the sum of all yielded values without tail.
  print('elapsed time =', main.elapsed_time())
  # Dump OSC commands score.
  print(score)
  # Render the score.
  score.render('test.aiff')


Timing in NRT
-------------

In NRT all commands and messages are synchronous. The mode runs in
:term:`logical time` and creates the OSC instructions with the proper
:term:`timetag`. No server is booted and no message is sent, all server
instructions are stored in an `OSC score` (which is a collection of bundles
ordered by time) that is later rendered by the command line server program.

When commands are issued from outside a routine, the time used to create the
:term:`timetag` is absolute, it means that the time reference is always zero.
Conversely, when they are issued from within routines :term:`logical time` is
used and time values are considered deltas from the current :term:`elapsed
time`.

::

  from sc3.all_nrt import *

  SystemDefs.add_synthdef('default')

  # Time 0
  play(midinote=48, sustain=6)
  play(midinote=55, sustain=6)

  @routine
  def melo():
      notes = [65, 64, 62, 63]
      rhyth = [2, 1, 1, 2]
      for n, r, in zip(notes, rhyth):
          play(midinote=n, dur=r, legato=1)
          yield r

  # Plays at time 0
  melo.play()

  # Also starts from time 0.
  play(midinote=60, sustain=6)

  score = main.process(1)
  score.render('test.aiff')

On the other hand, routines started within another routines will use the
current logical time of the containing routine.

::

  from sc3.all_nrt import *

  SystemDefs.add_synthdef('default')

  # Use tempo to play.
  clock = TempoClock(10)

  def melo():
      notes = Pwalk(
          [60, 62, 64, 67, 70, 72],
          Prand(range(-1, 3), 4)
      )
      for n in notes:
          play(midinote=n)
          yield 1

  @routine
  def texture():
      for i in range(20):
          # Start one after another 20 times.
          Routine(melo).play(clock)
          yield 2 + bi.choice([1, 0.5, 0.25])

  texture.play(clock)
  score = main.process(1)
  score.render('test.aiff')

.. note:

  There are more easy ways to do sequences with patterns which are not covered
  here.
