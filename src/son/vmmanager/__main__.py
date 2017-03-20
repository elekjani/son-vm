from son.vmmanager import server_configuariton
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
import argparse
import os

if __name__ == '__main__':
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--config','-c', action='append', dest='config_files', default=[])
    args = parser.parse_args()
    address, port, processors = server_configuration.parse_configuration_files(args.config_files)

    serverAddress = "tcp:{}:interface={}".format(port, address)
    logger.info("Starting server on %s" % serverAddress)
    endpoint = serverFromString(reactor, )

    factory = JsonMsgReaderFactory()
    for p in processors.keys():
        factory.addProcessor(p)

    endpoint.listen(factory)

    reactor.run()
