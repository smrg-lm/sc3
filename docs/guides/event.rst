.. _event:

.. warning:: Under construction.

Events
======

The library has basic support for events and patterns. However it differs from
the original implementation to keep basic functionality as simple and fast as
possible. Because of that, the only user level supported event type is
:class:`NoteEvent<sc3.seq.event.NoteEvent>` which has all the keys sets of the
original 'note' event. The event types necessary for
:class:`Pmono<sc3.seq.patterns.eventpatterns.Pmono>` are implemented internally
(with support for `PmonoArtic` integrated through the ``articulate`` argument).
Nevertheless, it's easy to create new event types in a possible future.

Events are Python dictionaries with extended functionality that mimics
SuperCollider's `Environment` class, although they are not environments here
and don't have exactly the same behavior.

Events are created through the :class:`sc3.seq.event.event` which in fact is
a subclass `dict` with the particularity that event instances are callable to
implement default key values.

::

  e = event()  # Create a NoteEvent type by defaults
  print(e)  # An empty NoteEvent({}) dictionary
  e['freq']  # KeyError
  e('freq')  # As callable returns the default freq value
  e.play()  # Play the event.

Event keys are organized in sets as in SuperCollider, each key set may define
the value of related keys if they are chained and so on. The way to obtain the
value of a given default key is to invoke the key with parenthesis instead of
brackets. The main use for events is to perform notes by sending a bundle with
all the required data and setting the release command if applicable.

The sc3 builtin function :meth:`play<sc3.base.play.play>` knows how to play
events if invoked with keyword only arguments or by passing in a dict object.

::

  play()  # Plays the default NoteEvent.
  play(midinote=69, dur=3)  # Keyword only arguments
  play({'midinote': 69, 'dur': 3})  # Dictionary
  play({'midinote': 69}, dur=3)  # Mixed (same interface as dict)

Using ``play`` as the interface makes it easy to use plain Python dictionaries
as data structures for storing data while also performing default keys lookup
through :class:`event<sc3.seq.event.event>`. This way, concrete event instances
are disposable, they are only used to interpret the keys and build the
messages.

.. note:

  As in SuperCollider, the play function also knows to play lambdas, and
  buffers.
