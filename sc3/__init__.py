
__version__ = '1.0.0a4'
__all__ = ['base', 'seq', 'synth']


### Library configuration ###

LIB_MODE = 'rt'
LIB_PORT = 57120
LIB_PORT_RANGE = 10
LIB_SETUP_FILE = None


### Configure logger ###

# https://docs.python.org/3/howto/logging-cookbook.html#dealing-with-handlers-that-block

def _init_logger(verbosity, bloking=False):
    import queue
    import logging
    import logging.handlers
    import atexit

    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')

    if bloking:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    else:
        q = queue.Queue(-1)
        queue_handler = logging.handlers.QueueHandler(q)
        listener_handler = logging.StreamHandler()
        listener_handler.setFormatter(formatter)
        listener = logging.handlers.QueueListener(q, listener_handler)
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)

        listener.start()
        atexit.register(listener.stop)

    root_logger.setLevel(verbosity)

### Init library ###

_libsc3_initialized = False

def init(mode='rt', verbosity='INFO'):
    global _libsc3_initialized

    if _libsc3_initialized:
        return

    mode = mode.lower()
    _init_logger(verbosity, True if mode == 'nrt' else False)

    import sc3.base.main

    if mode == 'rt':
        sc3.base.main.main = sc3.base.main.RtMain
    elif mode == 'nrt':
        sc3.base.main.main = sc3.base.main.NrtMain
    else:
        raise ValueError(f"invalid mode '{mode}'")

    sc3.base.main.main._init()
    _libsc3_initialized = True
