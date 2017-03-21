from son.vmmanager.processors import utils

import unittest
import logging

class Runner(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % Runner.__name__)

    def tearDown(self):
        self.task.stop()

    def testStart(self):
        self.task = utils.Runner('echo Test text')
        self.task.start()
        self.assertEqual(self.task.getOutput(), 'Test text')
        self.assertEqual(self.task.isRunning(), True)



