
import logging as _logging

# This seems to be needed before any module logger is used.
# TODO: log level in user config file.
_logging.basicConfig(level=_logging.INFO)  # (format='%(levelname)s:%(name)s:%(message)s')

import sc3.base.main as _
