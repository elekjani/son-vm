from twisted.internet.protocol import Protocol, ClientFactory as CF
from twisted.internet import defer, reactor

import logging
import json

class ClientProtocol(Protocol):

    def __init__(self, config):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self._connection_defer = defer.Deferred()

    def onCallback(func):
        def _tmp(self, *args, **kwargs):
            returnDefer = defer.Deferred()

            def callAndSet():
                self._current_defer = defer.Deferred()
                returnValue = func(self, *args, **kwargs)
                self._current_defer.addCallback(
                    lambda r: returnDefer.callback(returnValue)
                )
                return self._current_defer

            ad = lambda d: callAndSet() if d is None else d.addCallback(ad)
            self._connection_defer.addCallback(ad)

            return returnDefer

        return _tmp

    def dataReceived(self, data):
        self._logPeer('Received data from')
        self.logger.info('Data: %s', data)
        self._current_defer.callback(None)

    def connectionMade(self):
        self._logPeer('Connection ready to')
        self._connection_defer.callback(None)

    def connectionLost(self, reason):
        self._logPeer('Connection lost to')
        self.logger.info('Reason: %s', reason)

    @onCallback
    def sendStart(self):
        self._logPeer('Sending start command to')
        jsonString = json.dumps({ 'command': 'start' })
        self.transport.write(jsonString.encode())
        return self

    @onCallback
    def sendConfig(self):
        self._logPeer('Sending configuration to')
        jsonString = json.dumps(self.config)
        self.transport.write(jsonString.encode())
        return self

    @onCallback
    def sendStop(self):
        self._logPeer('Sending stop command to')
        jsonString = json.dumps({ 'command': 'start' })
        self.transport.write(jsonString.encode())
        return self

    def _logPeer(self, message):
        dst = self.transport.getPeer()
        self.logger.info('%s %s:%s', message, dst.host, dst.port)


class ClientFactory(CF):

    def __init__(self, configs, isStopping = False, port = 38388):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.protocols = {}
        for host,config in configs:
            self.logger.info('Creating connection to %s:%s', host, port)
            self.protocols[host] = ClientProtocol(config)
            reactor.connectTCP(host, port, self)

        if isStopping:
            d = defer.gatherResults(
                [p.sendStop() for p in self.protocols.values()]
            )
            d.addCallback(lambda ds: defer.gatherResults(ds).addCallback(
                lambda r: reactor.stop()
            ))
        else:
            d = defer.gatherResults(
                [p.sendConfig() for p in self.protocols.values()]
            )
            d.addCallback(lambda r: [p.sendStart() for p in r])
            d.addCallback(lambda ds: defer.gatherResults(ds).addCallback(
                lambda r: reactor.stop()
            ))

    def buildProtocol(self, addr):
        self.logger.info('Building protocol for %s:%s', addr.host, addr.port)
        return self.protocols[addr.host]

    def startedConnecting(self, connector):
        dst = connector.getDestination()
        self.logger.info('Starting to connect to %s:%s', dst.host, dst.port)

    def clientConnectionLost(self, connector, reason):
        dst = connector.getDestination()
        self.logger.info('Lost connection to %s:%s', dst.host, dst.port)
        self.protocols[dst.host] = None

    def clientConnectionFailed(self, connector, reason):
        dst = connector.getDestination()
        self.logger.info('Connection failed to %s:%s', dst.host, dst.port)
        self.logger.info('Reason: %s', reason)
        self.protocols[dst.host] = None
