from twisted.internet.protocol import Protocol, ClientFactory as CF
from twisted.internet import defer, reactor

import logging
import json

class ClientProtocol(Protocol):

    def __init__(self, config, connectionMadeDefer):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.connectionMadeDefer = connectionMadeDefer

    def dataReceived(self, data):
        dst = self.transport.getPeer()
        self.logger.info('Received data from %s:%s', dst.host, dst.port)
        self.logger.info('Data: %s', data)

    def connectionMade(self):
        dst = self.transport.getPeer()
        self.logger.info('Connection ready to %s:%s', dst.host, dst.port)
        self.connectionMadeDefer.callback(0)

    def connectionLost(self, reason):
        dst = self.transport.getPeer()
        self.logger.info('Connection lost to %s:%s', dst.host, dst.port)
        self.logger.info('Reason: %s', reason)

    def sendStart(self, startDefer = None):
        dst = self.transport.getPeer()
        self.logger.info('Sending start command to %s:%s', dst.host, dst.port)
        jsonString = json.dumps({ 'command': 'start' })
        self.transport.write(jsonString.encode())
        if starDefer is not None:
            startDefer.callback(0)

    def sendConfig(self, configDefer = None):
        dst = self.transport.getPeer()
        self.logger.info('Sending configuration to %s:%s', dst.host, dst.port)
        jsonString = json.dumps(self.config)
        self.transport.write(jsonString.encode())
        if configDefer is not None:
            configDefer.callback(0)


class ClientFactory(CF):

    def __init__(self, configs, port = 38388):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.protocols = {}
        self.configs = configs
        self.connectionDefers = {}
        for c in self.configs:
            self.connectionDefers[c[0]] = defer.Deferred()
            self.logger.info('Creating connection to %s:%s', c[0], port)
            reactor.connectTCP(c[0], port, self)

        defers = [d for d in self.connectionDefers.values()]
        self.connectionDefer = defer.gatherResults(defers)
        self.connectionDefer.addCallback(self.allConnected)

    def allConnected(self, result):
        for c in self.configs:
            self.protocols[c[0]].sendConfig()

        self.configurationDone(0)

    def configurationDone(self, result):
        for c in self.configs:
            self.protocols[c[0]].sendStart()

        self.startingDone(0)

    def startingDone(self, result):
        reactor.stop()

    def startedConnecting(self, connector):
        dst = connector.getDestination()
        self.logger.info('Starting to connect %s:%s', dst.host, dst.port)
        self.protocols[dst.host] = None

    def buildProtocol(self, addr):
        self.logger.info('Building protocol for %s:%s', addr.host, addr.port)
        config = [c[1] for c in self.configs if c[0] == addr.host]
        if len(config) is not 1:
            self.logger.error('Address %s is not found in configs', addr.host)
            reactor.stop()
            return
        protocol = ClientProtocol(config[0], self.connectionDefers[addr.host])
        self.protocols[addr.host] = protocol
        return protocol

    def clientConnectionLost(self, connector, reason):
        dst = connector.getDestination()
        self.logger.info('Lost connection to %s:%s', dst.host, dst.port)
        self.protocols[dst.host] = None

    def clientConnectionFailed(self, connector, reason):
        dst = connector.getDestination()
        self.logger.info('Connection failed to %s:%s', dst.host, dst.port)
        self.logger.info('Reason: %s', reason)
        self.protocols[dst.host] = None



