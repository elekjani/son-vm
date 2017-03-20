from configparser import ConfigParser

import logging
import os

NETWORK_SECTION = 'network'
NETWORK_SERVER_PORT = 'port'
NETWORK_SERVER_ADDRESS = 'address'

PROCESSORS_SECTION = 'processors'

DEFAULT_PORT = 38388
DEFAULT_ADDRESS = "0.0.0.0"

logger = logging.getLogger(__name__)

def parse_configuration_files(config_files):
    port = None
    address = None
    processors = {}
    for config_file in config_files:
        if not os.path.isfile(config_file):
            logger.warn('Configuration file "%s" does not exist.', config_file)
            continue

        logger.info('Parsing configuration file "%s"', config_file)
        conf_parser = ConfigParser()
        conf_parser.read(config_file)
        if conf_parser.has_section(NETWORK_SECTION):
            if conf_parser.has_option(NETWORK_SECTION, NETWORK_SERVER_PORT):
                p = conf_parser.getint(NETWORK_SECTION, NETWORK_SERVER_PORT)
                if port is None:
                    port = p
                    logger.info('Setting server port to "%d" from file "%s"',
                                port, config_file)
                else:
                    logger.warn('Port has been already set (%d)'
                                'Ignoring value "%d" from file "%s"',
                                port, p, config_file)

            if conf_parser.has_option(NETWORK_SECTION, NETWORK_SERVER_ADDRESS):
                a = conf_parser.get(NETWORK_SECTION, NETWORK_SERVER_ADDRESS)
                if address is None:
                    address = a
                    logger.info('Setting bind address to "%s" from file "%s"',
                                address, config_file)
                else:
                    logger.warn('Address has been already set (%s)'
                                'Ignoring value "%s" from file "%s"',
                                address, a, config_file)

        if conf_parser.has_section(PROCESSORS_SECTION):
            for p in conf_parser.options(PROCESSORS_SECTION):
                if p in processors:
                    logger.warn('Processor with name "%s" has been already'
                                'defined. Ignoring it from file "%s"',
                                p, config_file)
                    continue

                processors[p] = conf_parser.get(PROCESSORS_SECTION, p)
                logger.info('Adding processor "%s" (%s) from file %s',
                            p, processors[p], config_file)

    if port is None:
        port = DEFAULT_PORT

    if address is None:
        address = DEFAULT_ADDRESS

    return address, port, processors



