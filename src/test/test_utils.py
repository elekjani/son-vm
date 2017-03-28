from son.vmmanager.processors import utils

import tempfile
import unittest
import logging
import os.path

logging.basicConfig(level=logging.DEBUG)

class Runner(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % Runner.__name__)

    def tearDown(self):
        if self.task.isRunning():
            self.task.stop()

    def testStart(self):
        self.task = utils.Runner('echo Test text', start_shell=True)
        self.task.start()
        while self.task.isRunning(): pass
        self.task.stop()
        self.assertIn('Test text', self.task.getOutput())

    def testLogFile(self):
        with tempfile.TemporaryDirectory() as log_dir:
            self.task = utils.Runner('echo Test text',
                                     log_dir = log_dir,
                                     start_shell=True)
            self.task.start()
            while self.task.isRunning(): pass
            self.task.stop()
            self.assertIn('Test text', self.task.getOutput())
            self.assertEqual('', self.task.getOutput(stderr = True))

            stdout_content = ""
            with open(os.path.join(log_dir, "stdout")) as log_file:
                for line in log_file:
                    stdout_content += line

            stderr_content = ""
            with open(os.path.join(log_dir, "stderr")) as log_file:
                for line in log_file:
                    stderr_content += line

            self.assertIn('Test text', stdout_content)
            self.assertEqual('', stderr_content)
