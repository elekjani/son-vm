from son.vmmanager.jsonserver import IJsonProcessor, JsonMsgReaderFactory

from twisted.test import proto_helpers

import time
import threading
import subprocess
import unittest
import tempfile
import logging
import os
import io
import json

logging.basicConfig(level=logging.DEBUG)

class TestProcessor(IJsonProcessor):

    ANSWER = 'Everyting is fine'

    def __init__(self):
        self.logger = logging.getLogger(TestProcessor.__name__)

    def process(self, json):
        self.logger.info('TestProcessor has been called with msg: %s', json)
        return IJsonProcessor.Result(IJsonProcessor.Result.OK, self.ANSWER)


class JsonServer(unittest.TestCase):

    def testProtocol(self):
        self.logger = logging.getLogger('test.%s' % JsonServer.__name__)

        TEST_PROCESSOR = 'testProcessor'

        factory = JsonMsgReaderFactory()
        factory.addProcessor(TEST_PROCESSOR, TestProcessor())
        self.proto = factory.buildProtocol(('127.0.0.1', 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

        self.proto.dataReceived('{}'.encode('utf-8'))

        answer = self.tr.value()
        self.assertIsNotNone(answer)
        self.assertIsInstance(answer, bytes)

        answerDict = json.loads(answer.decode('utf-8'))
        self.assertIn(TEST_PROCESSOR, answerDict)
        testProcessorAnswer = json.loads(answerDict[TEST_PROCESSOR])

        self.assertIn(IJsonProcessor.Result.STATUS, testProcessorAnswer)
        self.assertEqual(testProcessorAnswer[IJsonProcessor.Result.STATUS],
                         IJsonProcessor.Result.OK)

        self.assertIn(IJsonProcessor.Result.MESSAGE, testProcessorAnswer)
        self.assertEqual(testProcessorAnswer[IJsonProcessor.Result.MESSAGE],
                         TestProcessor.ANSWER)

