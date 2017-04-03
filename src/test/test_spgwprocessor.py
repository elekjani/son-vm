import son.vmmanager.processors.spgw_processor as spgw_p
from son.vmmanager.processors.utils import CommandConfig

from unittest.mock import patch
from unittest.mock import Mock
import unittest
import tempfile
import logging
import os

logging.basicConfig(level=logging.DEBUG)

class SPGW_Processor(unittest.TestCase):

    @patch('son.vmmanager.processors.utils.Runner')
    @patch('son.vmmanager.processors.spgw_processor.SPGW_Configurator')
    @patch('son.vmmanager.processors.spgw_processor.SPGW_MessageParser')
    def testProcess(self, SPGW_MessageParserMock, SPGW_ConfiguratorMock, RunnerMock):
        SPGW_MessageParserMock.return_value = Mock(wraps = SPGW_MessageParserMock)
        SPGW_ConfiguratorMock.return_value = Mock(wraps = SPGW_ConfiguratorMock)
        RunnerMock.return_value = Mock(wraps = RunnerMock)

        config_dict = {}

        processor = spgw_p.SPGW_Processor()
        processor.process(config_dict)

        SPGW_MessageParserMock.assert_called_once_with(config_dict)
        SPGW_MessageParserMock.parse.assert_called_once()

        SPGW_ConfiguratorMock.assert_called_once()
        SPGW_ConfiguratorMock.configure.assert_called_once()

        RunnerMock.assert_called_once()

    @patch('son.vmmanager.processors.utils.Runner')
    @patch('son.vmmanager.processors.spgw_processor.SPGW_Configurator')
    @patch('son.vmmanager.processors.spgw_processor.SPGW_MessageParser')
    def testProcessIssueCommand(self, SPGW_MessageParserMock,
                                SPGW_ConfiguratorMock, RunnerMock):
        SPGW_MessageParserMock.return_value = Mock(wraps = SPGW_MessageParserMock)
        SPGW_MessageParserMock.parse.return_value = spgw_p.SPGW_Config(
            command = CommandConfig.START)
        SPGW_ConfiguratorMock.return_value = Mock(wraps = SPGW_ConfiguratorMock)
        RunnerMock.return_value = Mock(wraps = RunnerMock)

        config_dict = {}

        processor = spgw_p.SPGW_Processor()
        processor.process(config_dict)

        SPGW_MessageParserMock.assert_called_once_with(config_dict)
        SPGW_MessageParserMock.parse.assert_called_once()

        SPGW_ConfiguratorMock.assert_called_once()
        SPGW_ConfiguratorMock.configure.assert_called_once()

        RunnerMock.assert_called_once()
        RunnerMock.start.assert_called_once()

        SPGW_MessageParserMock.parse.return_value = spgw_p.SPGW_Config(
            command = CommandConfig.STOP)
        processor.process(config_dict)

        RunnerMock.stop.assert_called_once()

        SPGW_MessageParserMock.parse.return_value = spgw_p.SPGW_Config(
            command = CommandConfig.RESTART)
        processor.process(config_dict)

        RunnerMock.restart.assert_called_once()

        SPGW_MessageParserMock.parse.return_value = spgw_p.SPGW_Config(
            command = CommandConfig.STATUS)
        processor.process(config_dict)

        self.assertEqual(RunnerMock.getOutput.call_count, 2)


class SPGW_MsgParser(unittest.TestCase):
    def testFullConfigWithGarbage(self):
        CONF_SGI_IP = '30.30.30.30/24'
        CONF_S1U_IP = '20.20.20.20/16'
        COMMAND = 'start'

        config_dict = {
            'sgi_ip': CONF_SGI_IP,
            's1u_ip': CONF_S1U_IP,
            'command': COMMAND,
            'garbage': {'key1': 1, 'key2': 2}
        }
        parser = spgw_p.SPGW_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.sgi_ip, CONF_SGI_IP)
        self.assertEqual(config.s1u_ip, CONF_S1U_IP)
        self.assertEqual(config.command, CommandConfig.START)

    def testInvalidCommand(self):

        config_dict = {
            'command': 'invalid_command'
        }
        parser = spgw_p.SPGW_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.command, None)


class SPGW_Configurator(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % self.__class__.__name__)

        os_fd, self.spgw_config = tempfile.mkstemp()
        os.close(os_fd)

    def tearDown(self):
        os.remove(self.spgw_config)

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

    def testUpdateSPGWConfig(self):
        S11_INTERFACE = 'SGW_INTERFACE_NAME_FOR_S11'
        S11_IP = 'SGW_IPV4_ADDRESS_FOR_S11'
        SGI_INTERFACE = 'PGW_INTERFACE_NAME_FOR_SGI'
        S1U_IP = 'SGW_IPV4_ADDRESS_FOR_S1U_S12_S4_UP'
        self.writeContent('%s = "lo"\n' % S11_INTERFACE, self.spgw_config)
        self.writeContent('%s = "1.1.1.1/8"\n' % S11_IP, self.spgw_config)
        self.writeContent('%s = "eth2"\n' % SGI_INTERFACE, self.spgw_config)
        self.writeContent('%s = "3.3.3.3/32"\n' % S1U_IP, self.spgw_config)

        CONF_S11_INTERFACE = 'eth0'
        CONF_SGI_INTERFACE = 'eth2'
        CONF_SGI_IP = '30.30.30.30/24'
        CONF_S1U_IP = '20.20.20.20/16'

        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'

        ip2interface = {
            SPGW_IP: CONF_S11_INTERFACE,
            CONF_SGI_IP: CONF_SGI_INTERFACE
        }

        configurator = spgw_p.SPGW_Configurator(self.spgw_config)

        configurator.getInterfacesName = \
            lambda ip: ip2interface[ip] if ip in ip2interface else None

        config = spgw_p.SPGW_Config(sgi_ip = CONF_SGI_IP,
                                    s1u_ip = CONF_S1U_IP,
                                    mme_host = MME_HOST, mme_ip = MME_IP,
                                    hss_host = HSS_HOST, hss_ip = HSS_IP,
                                    spgw_host = SPGW_HOST, spgw_ip = SPGW_IP)

        configurator.configure(config)

        spgw_config = self.getContent(self.spgw_config)
        self.assertEqual(len(spgw_config.splitlines()), 4)
        self.assertIn('%s = "%s"' % (S11_INTERFACE, CONF_S11_INTERFACE), spgw_config)
        self.assertIn('%s = "%s"' % (S11_IP, SPGW_IP), spgw_config)
        self.assertIn('%s = "%s"' % (SGI_INTERFACE, CONF_SGI_INTERFACE), spgw_config)
        self.assertIn('%s = "%s"' % (S1U_IP, CONF_S1U_IP), spgw_config)
