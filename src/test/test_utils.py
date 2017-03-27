from son.vmmanager.processors import utils

import unittest
import logging

class Runner(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % Runner.__name__)

    def tearDown(self):
        if self.task.isRunning():
            self.task.stop()

    def testStart(self):
        self.task = utils.Runner('echo Test text', True)
        self.task.start()
        while self.task.isRunning(): pass
        self.task.stop()
        self.assertIn('Test text', self.task.getOutput())
