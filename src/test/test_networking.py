from son.vmmanager.jsonserver import JsonMsgReader
from son.vmmanager.jsonserver import JsonMsgReaderFactory
from son.vmmanager.jsonserver import IJsonProcessor
from twisted.test import proto_helpers

import unittest
import logging

logging.basicConfig(level=logging.DEBUG)

class VMManagerNetworking(unittest.TestCase):

    HOST = "127.0.0.1"
    PORT = 38389

    def _setUp(self, processors = []):
        self.factory = JsonMsgReaderFactory()
        for p in processors:
            self.factory.addProcessor(p)
        self.proto = self.factory.buildProtocol(
            (VMManagerNetworking.HOST, VMManagerNetworking.PORT))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

    def testDataIsReceived(self):
        TEST_DATA = '{"key1": 1'
        self._setUp()
        self.proto.dataReceived(TEST_DATA)

        self.assertEqual(self.proto._data, TEST_DATA)

    def testProcessorIsCalled(self):
        class TestProcessor(IJsonProcessor):
            def __init__(self):
                self.passed_json = []

            def process(self, json):
                self.passed_json.append(json)

        testProcessor = TestProcessor()
        self._setUp([testProcessor])
        self.proto.dataReceived('{"key1": 1, "key2": 2}')

        self.assertEqual(len(testProcessor.passed_json), 1)
        self.assertIn("key1", testProcessor.passed_json[0])
        self.assertIn("key2", testProcessor.passed_json[0])
        self.assertEqual(testProcessor.passed_json[0]["key1"], 1)
        self.assertEqual(testProcessor.passed_json[0]["key2"], 2)

