
import queue
import logging
import logging.handlers
import atexit


__version__ = '0.6.0'


### Configure logger ###

# https://docs.python.org/3/howto/logging-cookbook.html#dealing-with-handlers-that-block

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

import sc3.base.main as _
