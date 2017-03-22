import importlib
import logging
import argparse
import os

from son.vmmanager import server_configuration
from son.vmmanager.jsonserver import JsonMsgReaderFactory
from twisted.internet.endpoints import TCP4ServerEndpoint, serverFromString
from twisted.internet import reactor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config','-c', action='append', dest='config_files', default=[])
    parser.add_argument('--verbose','-v', action='store_true', dest='verbose', default=False)
    args = parser.parse_args()
    address, port, processors = server_configuration.parse_configuration_files(args.config_files)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    serverAddress = "tcp:{}:interface={}".format(port, address)
    logger.info("Starting server on %s" % serverAddress)
    endpoint = serverFromString(reactor, serverAddress)

    factory = JsonMsgReaderFactory()
    for p in processors:
        full_name = processors[p]
        module_name = '.'.join(full_name.split('.')[:-1])
        class_name  = full_name.split('.')[-1]
        logger.info('Loading processor class %s from module %s'
                    ' for processor named %s', class_name, modulde_name, p)
        try:
            processorModule = importlib.import_module(module_name)
            processorClass = getattr(processorModule, class_name)
            factory.addProcessor(processorClass())
        except ModuleNotFoundError:
            logger.warn('No module named %s has been found', module_name)
        except AttributeError:
            logger.warn('No class named %s has been found in module %s',
                        class_name, module_name)

    endpoint.listen(factory)

    reactor.run()
