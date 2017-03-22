from son.vmmanager.jsonserver import IJsonProcessor

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

import time
import threading
import subprocess
import unittest
import tempfile
import logging
import os
import io

logging.basicConfig(level=logging.DEBUG)

class TestProcessor(IJsonProcessor):

    def __init__(self):
        self.logger = logging.getLogger(TestProcessor.__name__)

    def process(self, json):
        self.logger.info('TestProcessor has been called with msg: %s', json)

class TestProtocol(Protocol):
    def connectionMade(self):
        self.transport.write(str.encode("{}"))
        self.transport.loseConnection()


class TestClientFactory(ClientFactory):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def startedConnecting(self, connector):
        self.logger.debug('Started to connect.')

    def buildProtocol(self, addr):
        self.logger.debug('Connected.')
        return TestProtocol()

    def clientConnectionLost(self, connector, reason):
        self.logger.debug('Lost connection.  Reason: %s', reason)
        reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        self.logger.debug('Connection failed. Reason: %s', reason)


class JsonServer(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % JsonServer.__name__)
        self.conf_fd, self.conf_path = tempfile.mkstemp(text=True)
        os.close(self.conf_fd)

    def tearDown(self):
        os.remove(self.conf_path)

    def _write_config(self, config_string):
        with open(self.conf_path, 'w') as f:
            f.write(config_string)

    def gotProtocol(self, p):
        p.sendMessage("{}", self.logger)
        reactor.callLater(1, p.sendMessage, "{}", self.logger)
        reactor.callLater(2, p.transport.loseConnection)


    def testStartServer(self):
        self._write_config('''
                           [network]
                           address=127.0.0.1
                           port=11223

                           [processors]
                           testProcessor=test.test_server.TestProcessor
                           ''')

        os_fd, stdout_path = tempfile.mkstemp()
        os.close(os_fd)
        stdout_file = open(stdout_path, 'w')

        cmd = 'python -m son.vmmanager -c %s -v' % self.conf_path
        server_process = subprocess.Popen(cmd,
                                          stdin = subprocess.PIPE,
                                          stdout = stdout_file,
                                          stderr = subprocess.STDOUT,
                                          bufsize = 4096)

        reactor.connectTCP('127.0.0.1', 11223, TestClientFactory())
        reactor.run()

        time.sleep(2)

        stdout_file.flush()

        with open(stdout_path, 'r') as f:
            for line in f:
                self.logger.debug(line)

        server_process.kill()

