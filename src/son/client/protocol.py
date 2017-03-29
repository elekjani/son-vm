from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import defer

import json

class ClientProtocol(Protocol):

    def __init__(self, config, connectionMadeDefer):
        self.config = config
        self.connectionMadeDefer = connectionMadeDefer

    def dataReceived(self, data):
        pass

    def connectionMade(self):
        self.connectionMadeDefer.callback(0)

    def connectionLost(self, reason):
        pass

    def sendStart(self, startDefer):
        jsonString = json.dumps({ 'command': 'start' })
        self.transport.write(jsonString.encode())
        startDefer.callback(0)

    def sendConfig(self, configDefer):
        jsonString = json.dumps(jsonDict)
        self.transport.write(jsonString.encode())
        configDefer.callback(0)


class ClientFactory(ClientFactory):

    def __init__(self, configs, port = 38388):
        self.protocols = {}
        self.configs = configs
        self.connectionDefers = {}
        for c in self.configs:
            self.connectionDefers[c[0]] = defer.Deferred()
            reactor.connectTCP(c[0], port, self)

        defer.gatherResults(
            [d for d in self.connectionDefers.values()]
        ).addCallback(self.allConnected)

    def allConnected(self):
        configDefers = []
        for c in self.configs:
            d = defer.Deferred()
            self.protocols[c[0]].sendConfig(d)
            configDefers.append(d)

        defer.gatherResults(configDefers).addCallback(self.configurationDone)

    def configurationDone(self):
        startDefers = []
        for c in self.configs:
            d = defer.Deferred()
            self.protocols[c[0]].sendStart(d)
            startDefer.append(d)

        defer.gatherResults(startDefer).addCallback(self.startingDone)

    def startingDone(self):
        reactor.stop()

    def startedConnecting(self, connector):
        self.protocols[connection.getDestination().host] = None

    def buildProtocol(self, addr):
        protocol = ClientProtocol(self.configs[addr.host],
                                  self.connectionDefers[addr.host])
        self.protocols[addr.host] = protocol
        return protocol

    def clientConnectionLost(self, connector, reason):
        self.protocols[connection.getDestination().host] = None

    def clientConnectionFailed(self, connector, reason):
        self.protocols[connection.getDestination().host] = None



