.. _routine:

.. warning:: Under construction.

Routines, streams and logical time
==================================

Routines in SuperCollider are a special kind of generators that can be
scheduled in clocks and keep track of the passing of :term:`logical time`.
They are needed to schedule sequences in time that will generate jitter-free
OSC :term:`timetags<timetag>`.

Instances of routines are created as shown below, their only argument is a
function or generator function (a function that define yield statements).
When its generator iterator is exhausted routines raise a
:class:`StopStream<sc3.base.stream.StopStream>` exception which is a subclass
of `StopIteration`.

::

  def func():
      for i in range(3):
          print(i)
          yield 1

  r = Routine(func)
  next(r)  # 0
  next(r)  # 1
  next(r)  # 2
  next(r)  # StopStream

Routine objects can be more conveniently created using the decorator function
syntax as follow:

::

  @routine
  def r():
      for i in range(3):
          print(i)
          yield 1

  next(r)  # 0
  next(r)  # 1
  next(r)  # 2
  next(r)  # StopStream

Note that a routine object is both a generator function and iterator. To define
more than one routine with the same function use the object constructor.

The meaning of routines start to reveal when they are used along clocks. They
respond to the ``play``, ``pause``, ``resume`` and ``stop`` methods. The
``play`` method starts playing the routine in a clock, the default clock which
is :class:`SystemClock<sc3.base.clock.SystemClock>`.

::

  @routine
  def r():
      i = 0
      while True:
          print(i)
          i += 1
          yield 1

  r.play()  # Schedule the routine in a clock.
  r.pause()  # Stop the routine and remove form the clock.
  r.resume() # Resume form were it was.
  r.stop()  # Stop it for good.
  r.reset()  # Reinitialize it to play again from the beginning.
  # r.play()  # To start over.

When a routine is stopped it has to be reset in order to be used again. The
method ``reset`` sets it to the initial state, internally it also creates the
generator iterator again.

By the way, don't play an infinite loop without yield time, it will hang
everything.

.. TODO: An actual bundle example, maybe with event.


Timing
------

When routines are scheduled on clocks their yield value is used as wait time
for a next call or cancel its execution. When the return value is a number
(``int`` or ``float``) the clock takes this value to re-schedule the routine
after waiting that much seconds (if no tempo is used). When the generator
returns, or yields another type of value, the clocks leaves the routine.

The yielded values, as time, are used to wait (in :term:`physical time`) but
also define the :term:`logical time` which increments only from those values.
In other words, the logical time of a routine is the sum of all the yielded
values so far.

This way, when a routine is scheduled in Python its next call time may not be
precise, it may even have noticeable jitter under load, but if we use the
logical time to generate a :term:`timetag` each iteration the wait time sent to
the server will be precise.

Physical time can be accessed from ``main.elapsed__time()``, which is the time
in seconds since the librar started.

::

  @routine
  def r():
      while True:
          print(main.elapsed_time(), main.current_tt.seconds)
          yield 1

  r.play()

.. note::

  For most common cases it's not necessary to access routine's logical time,
  the library will manage timing internally.

In the example above we can compare how the decimal part of the logical time is
always the same while for ``elapsed_time()`` constantly changing. Whenever an
OSC bundle is sent from a routine playing on a clock the time used to define
its :term:`timetag` is the logical time.

This is important to keep in mind because is the only way to have precise
timing for rhythmic sequences in real time. And this is one of the two core
features of this library (the other being :term:`synthdef` building
capabilities).


Streams
-------

Streams are the counter part of Python's generators iterators but in a
SuperCollider way. Routines are the most commonly used stream but not all
streams are routines.

Streams support mathematical operations and behave, in concept, in a similar
way to signals represented by :term:`ugens<ugen>`). In the next example, the
routine object ``r`` is transposed by ``2`` and creates a
:class:`sc3.base.stream.BinaryOpStream`, the stream resulting from applying the
binary operator ``+``.

::

  @routine
  def r():
      for i in range(12):
          yield i

  t = r + 60
  next(t)  # 60
  next(t)  # 61

Special `builtin` methods like :meth:`sc3.AbstractObject.midicps` also apply
to streams.

::

  t = t.midicps()
  next(t)  # MIDI note 63 is ca. 293.6647 Hz.


Random numbers
--------------

Each :class:`sc3.base.stream.Routine` instance has a random number generator,
by default is inherited from its parent routine (or the main time thread) but
random seeds can be changed per routine object. To make use of this
functionality its necessary to use the `builtin` random functions or methods
which are aware of routines.

::

  @routine
  def r():
      while True:
          yield bi.rrand(48, 60)

  next(r)  # A random number.
  r.rand_seed = 12345
  next(r)  # First number.
  next(r)  # Second number.
  r.rand_seed = 12345
  next(r)  # Same first.
  next(r)  # Same second.


Blocking the main thread
------------------------

Because each clock run in its own thread, for real time scripts, the main
thread needs to block until routines' execution finishes or the script will
quit before time.

In the next example the main thread blocks after spawning several routines and
resumes when ``r`` is finished so the script can exit.

::

  #!/usr/bin/env python3

  from sc3.all import *

  @routine
  def r():
      for i in range(13):
          play(midinote=60 + i, sustain=0.05)
          yield 0.25
      main.resume()  # Resume the main thread.

  # Play r after the server has booted.
  s.boot(on_complete=lambda: r.play())

  # Wait on the main thread and compensate
  # latency with end time before exit.
  main.wait(s.latency)
