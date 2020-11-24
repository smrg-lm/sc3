.. _nonrealtime:

.. warning:: Under construction.

Non real time mode
==================

The library can also run in non real time (NRT) mode. This mode
is based on the `NRTClock` :term:`quark`, with the addition that
the whole library timing is managed in NRT.

In NRT, clocks, routines and random generators work with the same
interface as real time. It was made so code can be easily adapted
or run in both modes without changes.

.. note::
   It's not possible to run the library in both RT and NRT at the
   same time because clocks and :term:`elapsed time` are internally
   managed in different ways. To run a NRT script from a RT library
   instance could be done by creating a sub-process that starts a
   new interpreter.

The following example can be run as command line script:

::

  #!/usr/bin/env python3

  # Init NRT mode and import all.
  from sc3.all_nrt import *

  # Load default synthdef.
  SystemDefs.add_sdef('default')

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

In NRT all commands and messages are synchronous because the
mode captures the term:`logical time` and create the OSC
instructions with the proper :term:`timetag`. No server is
running and no message is sent, all server instructions are
stored in an `OSC score` (which is a collection of bundles
ordered by time) that is later rendered by the command line
server program.

When commands are issued from outside a routine, the time used
to create the :term:`timetag` is absolute, it means that the
time reference is always zero. Conversely, when they are issued
from within routines :term:`logical time` is used and time values
are considered deltas from the current :term:`elapsed time`.

::
  # Missing Example...
