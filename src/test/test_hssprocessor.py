import son.vmmanager.processors.hss_processor as hss_p

from unittest.mock import patch
from unittest.mock import Mock
import unittest
import tempfile
import logging
import os

logging.basicConfig(level=logging.DEBUG)

class HSS_Processor(unittest.TestCase):

    @patch('son.vmmanager.processors.utils.Runner')
    @patch('son.vmmanager.processors.hss_processor.HSS_Configurator')
    @patch('son.vmmanager.processors.hss_processor.HSS_MessageParser')
    def testProcess(self, HSS_MessageParserMock, HSS_ConfiguratorMock, RunnerMock):
        HSS_MessageParserMock.return_value = Mock(wraps = HSS_MessageParserMock)
        HSS_ConfiguratorMock.return_value = Mock(wraps = HSS_ConfiguratorMock)
        RunnerMock.return_value = Mock(wraps = RunnerMock)

        config_dict = {}

        processor = hss_p.HSS_Processor()
        processor.process(config_dict)

        HSS_MessageParserMock.assert_called_once_with(config_dict)
        HSS_MessageParserMock.parse.assert_called_once()

        HSS_ConfiguratorMock.assert_called_once()
        HSS_ConfiguratorMock.configure.assert_called_once()

        RunnerMock.assert_called_once()

    @patch('son.vmmanager.processors.utils.Runner')
    @patch('son.vmmanager.processors.hss_processor.HSS_Configurator')
    @patch('son.vmmanager.processors.hss_processor.HSS_MessageParser')
    def testProcessIssueCommand(self, HSS_MessageParserMock,
                                HSS_ConfiguratorMock, RunnerMock):
        HSS_MessageParserMock.return_value = Mock(wraps = HSS_MessageParserMock)
        HSS_MessageParserMock.parse.return_value = hss_p.HSS_Config(command = 'start')
        HSS_ConfiguratorMock.return_value = Mock(wraps = HSS_ConfiguratorMock)
        RunnerMock.return_value = Mock(wraps = RunnerMock)

        config_dict = {}

        processor = hss_p.HSS_Processor()
        processor.process(config_dict)

        HSS_MessageParserMock.assert_called_once_with(config_dict)
        HSS_MessageParserMock.parse.assert_called_once()

        HSS_ConfiguratorMock.assert_called_once()
        HSS_ConfiguratorMock.configure.assert_called_once()

        RunnerMock.assert_called_once()
        RunnerMock.start.assert_called_once()

        HSS_MessageParserMock.parse.return_value = hss_p.HSS_Config(command = 'stop')
        processor.process(config_dict)

        RunnerMock.stop.assert_called_once()

        HSS_MessageParserMock.parse.return_value = hss_p.HSS_Config(command = 'restart')
        processor.process(config_dict)

        RunnerMock.restart.assert_called_once()


class HSS_MsgParser(unittest.TestCase):
    def testFullConfigWithGarbage(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        MYSQL_USER, MYSQL_PASS = 'root', 'hurka'
        COMMAND = 'start'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP, 'garbage': 123},
                'hss': {'host_name': HSS_HOST, 'ip': HSS_IP},
                'spgw': {'host_name': SPGW_HOST, 'ip': SPGW_IP},
                'garbage': [1,2,3]
            },
            'mysql': {
                'user': MYSQL_USER,
                'pass': MYSQL_PASS
            },
            'command': COMMAND,
            'garbage': {'key1': 1, 'key2': 2}
        }
        parser = hss_p.HSS_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, MME_HOST)
        self.assertEqual(config.mme_ip, MME_IP)
        self.assertEqual(config.hss_host, HSS_HOST)
        self.assertEqual(config.hss_ip, HSS_IP)
        self.assertEqual(config.spgw_host, SPGW_HOST)
        self.assertEqual(config.spgw_ip, SPGW_IP)
        self.assertEqual(config.mysql_user, MYSQL_USER)
        self.assertEqual(config.mysql_pass, MYSQL_PASS)
        self.assertEqual(config.command, COMMAND)

    def testPartlyHostConfig(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST = 'spgw.domain.my', '10.0.0.4/24'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP},
                'hss': {'ip': HSS_IP},
                'spgw': {'host_name': SPGW_HOST}
            }
        }
        parser = hss_p.HSS_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, MME_HOST)
        self.assertEqual(config.mme_ip, MME_IP)
        self.assertEqual(config.hss_host, None)
        self.assertEqual(config.hss_ip, None)
        self.assertEqual(config.spgw_host, None)
        self.assertEqual(config.spgw_ip, None)

    def testValidHostsConfig(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP},
                'hss': {'host_name': HSS_HOST, 'ip': HSS_IP},
                'spgw': {'host_name': SPGW_HOST, 'ip': SPGW_IP}
            }
        }
        parser = hss_p.HSS_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, MME_HOST)
        self.assertEqual(config.mme_ip, MME_IP)
        self.assertEqual(config.hss_host, HSS_HOST)
        self.assertEqual(config.hss_ip, HSS_IP)
        self.assertEqual(config.spgw_host, SPGW_HOST)
        self.assertEqual(config.spgw_ip, SPGW_IP)

    def testValidFullConfig(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        MYSQL_USER, MYSQL_PASS = 'root', 'hurka'
        COMMAND = 'start'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP},
                'hss': {'host_name': HSS_HOST, 'ip': HSS_IP},
                'spgw': {'host_name': SPGW_HOST, 'ip': SPGW_IP}
            },
            'mysql': {
                'user': MYSQL_USER,
                'pass': MYSQL_PASS
            },
            'command': COMMAND
        }
        parser = hss_p.HSS_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, MME_HOST)
        self.assertEqual(config.mme_ip, MME_IP)
        self.assertEqual(config.hss_host, HSS_HOST)
        self.assertEqual(config.hss_ip, HSS_IP)
        self.assertEqual(config.spgw_host, SPGW_HOST)
        self.assertEqual(config.spgw_ip, SPGW_IP)
        self.assertEqual(config.mysql_user, MYSQL_USER)
        self.assertEqual(config.mysql_pass, MYSQL_PASS)
        self.assertEqual(config.command, COMMAND)

    def testInvlidIP(self):
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.2'

        config_dict = {
            'hosts': {
                'hss': {'host_name': HSS_HOST, 'ip': HSS_IP}
            }
        }
        parser = hss_p.HSS_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.hss_host, None)
        self.assertEqual(config.hss_ip, None)

    def testInvalidCommand(self):

        config_dict = {
            'command': 'invalid_command'
        }
        parser = hss_p.HSS_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.command, None)


class HSS_Configurator(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % self.__class__.__name__)

        os_fd, self.host_file = tempfile.mkstemp()
        os.close(os_fd)
        os_fd, self.hss_config = tempfile.mkstemp()
        os.close(os_fd)

    def tearDown(self):
        os.remove(self.host_file)
        os.remove(self.hss_config)

    def ip(self, masked_ip):
        return masked_ip.split('/')[0] if masked_ip is not None else None

    def getContent(self, file_path):
        content = ""
        with open(file_path, 'r') as f:
            for line in f:
                content += '%s' % line

        self.logger.debug('Content read from %s:\n%s', file_path, content)

        return content

    def writeContent(self, content, file_path):
        self.logger.debug('Writing the following content to %s:\n%s',
                          file_path, content)

        with open(file_path, 'a') as f:
            f.write(content)

        self.logger.debug('Content written to file %s:\n%s',
                          file_path, self.getContent(file_path))

    def testWriteHostFile(self):
        configurator = hss_p.HSS_Configurator(self.hss_config,
                                              self.host_file)


        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'

        config = hss_p.HSS_Config(mme_host = MME_HOST, mme_ip = MME_IP,
                                  hss_host = HSS_HOST, hss_ip = HSS_IP,
                                  spgw_host = SPGW_HOST, spgw_ip = SPGW_IP)

        configurator.configure(config)

        host_file_content = self.getContent(self.host_file)

        self.assertEqual(len(host_file_content.splitlines()), 2)
        self.assertIn('%s %s' % (self.ip(MME_IP), MME_HOST), host_file_content)
        self.assertIn('%s %s' % (self.ip(HSS_IP), HSS_HOST), host_file_content)

    def testUpdateHostFile(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        CUSTOM_H, CUSTOM_IP = 'custom_host', '11.11.11.11'

        self.writeContent('11.0.0.1 %s\n' % MME_HOST, self.host_file)
        self.writeContent('12.0.0.1 %s\n' % HSS_HOST, self.host_file)
        self.writeContent('%s %s\n' % (CUSTOM_IP, CUSTOM_H), self.host_file)

        configurator = hss_p.HSS_Configurator(self.hss_config,
                                              self.host_file)

        config = hss_p.HSS_Config(mme_host = MME_HOST, mme_ip = MME_IP,
                                  hss_host = HSS_HOST, hss_ip = HSS_IP,
                                  spgw_host = SPGW_HOST, spgw_ip = SPGW_IP)

        configurator.configure(config)

        host_file_content = self.getContent(self.host_file)

        self.assertEqual(len(host_file_content.splitlines()), 3)
        self.assertIn('%s %s' % (self.ip(MME_IP), MME_HOST), host_file_content)
        self.assertIn('%s %s' % (self.ip(HSS_IP), HSS_HOST), host_file_content)
        self.assertIn('%s %s' % (CUSTOM_IP, CUSTOM_H), host_file_content)

    def testUpdateHSSConfig(self):
        HSS_MYSQL_USER = 'user'
        HSS_MYSQL_PASS = 'pass'
        self.writeContent('%s = "@MYSQL_user@"\n' % HSS_MYSQL_USER, self.hss_config)
        self.writeContent('%s = "@MYSQL_pass@"\n' % HSS_MYSQL_PASS, self.hss_config)

        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        MYSQL_USER, MYSQL_PASS = 'root', 'hurka'

        configurator = hss_p.HSS_Configurator(self.hss_config,
                                              self.host_file)

        config = hss_p.HSS_Config(mme_host = MME_HOST, mme_ip = MME_IP,
                                  hss_host = HSS_HOST, hss_ip = HSS_IP,
                                  spgw_host = SPGW_HOST, spgw_ip = SPGW_IP,
                                  mysql_user = MYSQL_USER,
                                  mysql_pass = MYSQL_PASS)

        configurator.configure(config)

        hss_config = self.getContent(self.hss_config)
        self.assertEqual(len(hss_config.splitlines()), 2)
        self.assertIn('%s = "%s"' % (HSS_MYSQL_USER, MYSQL_USER), hss_config)
        self.assertIn('%s = "%s"' % (HSS_MYSQL_PASS, MYSQL_PASS), hss_config)
