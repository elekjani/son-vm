from son.vmmanager import server_configuration as sc

import unittest
import logging
import tempfile
import os

logging.basicConfig(level=logging.DEBUG)

class ServerConfigurationParsing(unittest.TestCase):

    def setUp(self):
        self.conf_fd, self.conf_path = tempfile.mkstemp(text=True)
        os.close(self.conf_fd)

    def tearDown(self):
        os.remove(self.conf_path)

    def _write_config(self, config_string):
        with open(self.conf_path, 'w') as f:
            f.write(config_string)

    def testDefaultConfig(self):
        address, port, processors = sc.parse_configuration_files([self.conf_path])

        self.assertEqual(address, sc.DEFAULT_ADDRESS)
        self.assertEqual(port, sc.DEFAULT_PORT)
        self.assertEqual(len(processors), 0)

    def testNetworkingConfig(self):
        self._write_config('''
                           [network]
                           port=11111
                           address=10.0.0.1
                           ''')
        address, port, processors = sc.parse_configuration_files([self.conf_path])

        self.assertEqual(address, "10.0.0.1")
        self.assertEqual(port, 11111)
        self.assertEqual(len(processors), 0)

    def testPorcessorConfig(self):
        self._write_config('''
                           [processors]
                           firstTestProcessor=module.name.Processor
                           secondTestProcessor=module.name.Processor2
                           ''')

        address, port, processors = sc.parse_configuration_files([self.conf_path])

        self.assertEqual(len(processors), 2)
        self.assertIn('firsttestprocessor', processors)
        self.assertEqual(processors['firsttestprocessor'], 'module.name.Processor')
        self.assertIn('secondtestprocessor', processors)
        self.assertEqual(processors['secondtestprocessor'], 'module.name.Processor2')
