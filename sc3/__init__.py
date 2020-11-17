
__version__ = '1.0.0a'
__all__ = ['base', 'seq', 'synth']


### Configure logger ###

# https://docs.python.org/3/howto/logging-cookbook.html#dealing-with-handlers-that-block

def _init_logger():
    import queue
    import logging
    import logging.handlers
    import atexit

    q = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(q)
    listener_handler = logging.StreamHandler()
    listener = logging.handlers.QueueListener(q, listener_handler)

    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    listener_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel('INFO')
    root_logger.addHandler(queue_handler)

    listener.start()
    atexit.register(listener.stop)


### Init library ###

_libsc3_initialized = False

def init(mode='rt'):
    global _libsc3_initialized
    if _libsc3_initialized:
        return

    _init_logger()

    import sc3.base.main
    import sc3.base.classlibrary
    import sc3.seq.pattern  # Has late_imports and is not imported by main tree.

    mode = mode.lower()
    if mode == 'rt':
        sc3.base.main.main = sc3.base.main.RtMain
    elif mode == 'nrt':
        sc3.base.main.main = sc3.base.main.NrtMain
    else:
        raise ValueError(f"invalid mode '{mode}'")

    sc3.base.main.main._init()
    sc3.base.classlibrary.ClassLibrary.init()
    if mode == 'nrt':
        # This is only for user convenience.
        import sc3.synth.server as srv
        srv.Server.default.latency = 0
        srv.Server.default.boot()  # Sets _status_watcher._has_booted = True
    sc3.base.main.main._startup()

    _libsc3_initialized = True
