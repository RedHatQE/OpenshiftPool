import os
import sys
import logging

from openshift_pool.exceptions import EnvarNotDefinedException

ENV = {}

for ev in ('WORKSPACE', ):
    try:
        ENV[ev] = os.environ[ev]
    except KeyError:
        raise EnvarNotDefinedException(ev)


def config_workspace_as_cwd():
    os.chdir(ENV['WORKSPACE'])


LOG_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(message)s')  # TODO: parameterize
LOG_LEVEL = logging.INFO  # TODO: parameterize
MAIN_LOG_FILE = f'{os.environ["WORKSPACE"]}/main_log.log'


def setup_logger(name, log_file, level=LOG_LEVEL) -> logging.Logger:
    """Function setup as many loggers as you want"""

    if not os.path.exists(log_file):
        dr = os.path.isdir(log_file)
        if not dr:
            os.makedirs(dr)
        with open(log_file, 'w'):
            pass
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(LOG_FORMATTER)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(LOG_FORMATTER)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


main_log = setup_logger('main_log', MAIN_LOG_FILE, level=LOG_LEVEL)
