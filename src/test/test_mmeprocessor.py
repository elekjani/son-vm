import son.vmmanager.processors.mme_processor as mme_p

from unittest.mock import patch
from unittest.mock import Mock
import unittest
import tempfile
import logging
import os

logging.basicConfig(level=logging.DEBUG)

class MME_Processor(unittest.TestCase):

    @patch('son.vmmanager.processors.utils.Runner')
    @patch('son.vmmanager.processors.mme_processor.MME_Configurator')
    @patch('son.vmmanager.processors.mme_processor.MME_MessageParser')
    def testProcess(self, MME_MessageParserMock, MME_ConfiguratorMock, RunnerMock):
        MME_MessageParserMock.return_value = Mock(wraps = MME_MessageParserMock)
        MME_ConfiguratorMock.return_value = Mock(wraps = MME_ConfiguratorMock)
        RunnerMock.return_value = Mock(wraps = RunnerMock)

        config_dict = {}

        processor = mme_p.MME_Processor()
        processor.process(config_dict)

        MME_MessageParserMock.assert_called_once_with(config_dict)
        MME_MessageParserMock.parse.assert_called_once()

        MME_ConfiguratorMock.assert_called_once()
        MME_ConfiguratorMock.configure.assert_called_once()

        RunnerMock.assert_called_once()

    @patch('son.vmmanager.processors.utils.Runner')
    @patch('son.vmmanager.processors.mme_processor.MME_Configurator')
    @patch('son.vmmanager.processors.mme_processor.MME_MessageParser')
    def testProcessIssueCommand(self, MME_MessageParserMock,
                                MME_ConfiguratorMock, RunnerMock):
        MME_MessageParserMock.return_value = Mock(wraps = MME_MessageParserMock)
        MME_MessageParserMock.parse.return_value = mme_p.MME_Config(command = 'start')
        MME_ConfiguratorMock.return_value = Mock(wraps = MME_ConfiguratorMock)
        RunnerMock.return_value = Mock(wraps = RunnerMock)

        config_dict = {}

        processor = mme_p.MME_Processor()
        processor.process(config_dict)

        MME_MessageParserMock.assert_called_once_with(config_dict)
        MME_MessageParserMock.parse.assert_called_once()

        MME_ConfiguratorMock.assert_called_once()
        MME_ConfiguratorMock.configure.assert_called_once()

        RunnerMock.assert_called_once()
        RunnerMock.start.assert_called_once()

        MME_MessageParserMock.parse.return_value = mme_p.MME_Config(command = 'stop')
        processor.process(config_dict)

        RunnerMock.stop.assert_called_once()

        MME_MessageParserMock.parse.return_value = mme_p.MME_Config(command = 'restart')
        processor.process(config_dict)

        RunnerMock.restart.assert_called_once()


class MME_MsgParser(unittest.TestCase):
    def testFullConfigWithGarbage(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        S11_INTERFACE = 'eth0'
        COMMAND = 'start'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP, 'garbage': 123},
                'hss': {'host_name': HSS_HOST, 'ip': HSS_IP},
                'spgw': {'host_name': SPGW_HOST, 'ip': SPGW_IP},
                'garbage': [1,2,3]
            },
            's11_interface': S11_INTERFACE,
            'command': COMMAND,
            'garbage': {'key1': 1, 'key2': 2}
        }
        parser = mme_p.MME_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, MME_HOST)
        self.assertEqual(config.mme_ip, MME_IP)
        self.assertEqual(config.hss_host, HSS_HOST)
        self.assertEqual(config.hss_ip, HSS_IP)
        self.assertEqual(config.spgw_host, SPGW_HOST)
        self.assertEqual(config.spgw_ip, SPGW_IP)
        self.assertEqual(config.s11_interface, S11_INTERFACE)
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
        parser = mme_p.MME_MessageParser(config_dict)
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
        parser = mme_p.MME_MessageParser(config_dict)
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
        S11_INTERFACE = 'eth0'
        COMMAND = 'start'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP},
                'hss': {'host_name': HSS_HOST, 'ip': HSS_IP},
                'spgw': {'host_name': SPGW_HOST, 'ip': SPGW_IP}
            },
            's11_interface': S11_INTERFACE,
            'command': COMMAND
        }
        parser = mme_p.MME_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, MME_HOST)
        self.assertEqual(config.mme_ip, MME_IP)
        self.assertEqual(config.hss_host, HSS_HOST)
        self.assertEqual(config.hss_ip, HSS_IP)
        self.assertEqual(config.spgw_host, SPGW_HOST)
        self.assertEqual(config.spgw_ip, SPGW_IP)
        self.assertEqual(config.s11_interface, S11_INTERFACE)
        self.assertEqual(config.command, COMMAND)

    def testInvlidIP(self):
        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2'

        config_dict = {
            'hosts': {
                'mme': {'host_name': MME_HOST, 'ip': MME_IP}
            }
        }
        parser = mme_p.MME_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.mme_host, None)
        self.assertEqual(config.mme_ip, None)

    def testInvalidCommand(self):

        config_dict = {
            'command': 'invalid_command'
        }
        parser = mme_p.MME_MessageParser(config_dict)
        config = parser.parse()

        self.assertEqual(config.command, None)


class MME_Configurator(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger('test.%s' % self.__class__.__name__)

        os_fd, self.host_file = tempfile.mkstemp()
        os.close(os_fd)
        os_fd, self.mme_config = tempfile.mkstemp()
        os.close(os_fd)
        os_fd, self.mme_fd_config = tempfile.mkstemp()
        os.close(os_fd)

    def tearDown(self):
        os.remove(self.host_file)
        os.remove(self.mme_config)
        os.remove(self.mme_fd_config)

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
        configurator = mme_p.MME_Configurator(self.mme_config,
                                              self.mme_fd_config,
                                              self.host_file)


        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'

        config = mme_p.MME_Config(mme_host = MME_HOST, mme_ip = MME_IP,
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

        configurator = mme_p.MME_Configurator(self.mme_config,
                                              self.mme_fd_config,
                                              self.host_file)

        config = mme_p.MME_Config(mme_host = MME_HOST, mme_ip = MME_IP,
                                  hss_host = HSS_HOST, hss_ip = HSS_IP,
                                  spgw_host = SPGW_HOST, spgw_ip = SPGW_IP)

        configurator.configure(config)

        host_file_content = self.getContent(self.host_file)

        self.assertEqual(len(host_file_content.splitlines()), 3)
        self.assertIn('%s %s' % (self.ip(MME_IP), MME_HOST), host_file_content)
        self.assertIn('%s %s' % (self.ip(HSS_IP), HSS_HOST), host_file_content)
        self.assertIn('%s %s' % (CUSTOM_IP, CUSTOM_H), host_file_content)

    def testUpdateMMEConfig(self):
        MME_INTF_S11 = 'MME_INTERFACE_NAME_FOR_S11_MME'
        MME_IP_S11 = 'MME_IPV4_ADDRESS_FOR_S11_MME'
        MME_IP_S1 = 'MME_IPV4_ADDRESS_FOR_S1_MME'
        SPGW_IP_S11 = 'SGW_IPV4_ADDRESS_FOR_S11'
        self.writeContent('%s = "lo"\n' % MME_INTF_S11, self.mme_config)
        self.writeContent('%s = "1.1.1.1/8"\n' % MME_IP_S11, self.mme_config)
        self.writeContent('%s = "2.2.2.2/16"\n' % MME_IP_S1, self.mme_config)
        self.writeContent('%s = "3.3.3.3/32"\n' % SPGW_IP_S11, self.mme_config)

        MME_HOST, MME_IP = 'mme.domain.my', '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.domain.my', '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        S11_INTERFACE = 'eth0'

        configurator = mme_p.MME_Configurator(self.mme_config,
                                              self.mme_fd_config,
                                              self.host_file)

        config = mme_p.MME_Config(mme_host = MME_HOST, mme_ip = MME_IP,
                                  hss_host = HSS_HOST, hss_ip = HSS_IP,
                                  spgw_host = SPGW_HOST, spgw_ip = SPGW_IP,
                                  s11_interface = S11_INTERFACE)

        configurator.configure(config)

        mme_config = self.getContent(self.mme_config)
        self.assertEqual(len(mme_config.splitlines()), 4)
        self.assertIn('%s = "%s"' % (MME_INTF_S11, S11_INTERFACE), mme_config)
        self.assertIn('%s = "%s"' % (MME_IP_S11, MME_IP), mme_config)
        self.assertIn('%s = "%s"' % (MME_IP_S1, MME_IP), mme_config)
        self.assertIn('%s = "%s"' % (SPGW_IP_S11, SPGW_IP), mme_config)

    def testUpdateMMEFDConfig(self):
        IDENTITY = 'Identity'
        REALM = 'Realm'
        rEALM = 'realm'
        CONNECT_PEER = 'ConnectPeer'
        CONNECT_TO = 'ConnectTo'
        OTHER_CONFIGS = 'otherconfigs'
        CONNECT_LINE = '%s = "hss.host" { %s; %s = "127.0.0.1"; %s = "hss.realm";};\n'
        self.writeContent('%s = "myIdentity"\n' % IDENTITY, self.mme_fd_config)
        self.writeContent('%s = "myRealm"\n' % REALM, self.mme_fd_config)
        self.writeContent(CONNECT_LINE %
                          (CONNECT_PEER, OTHER_CONFIGS, CONNECT_TO, rEALM),
                          self.mme_fd_config)

        REALM_VALUE = 'domain.my'
        MME_HOST, MME_IP = 'mme.%s' % REALM_VALUE, '10.0.0.2/24'
        HSS_HOST, HSS_IP = 'hss.%s' % REALM_VALUE, '10.0.0.3/24'
        SPGW_HOST, SPGW_IP = 'spgw.%s' % REALM_VALUE, '10.0.0.4/24'
        S11_INTERFACE = 'eth0'

        configurator = mme_p.MME_Configurator(self.mme_config,
                                              self.mme_fd_config,
                                              self.host_file)

        config = mme_p.MME_Config(mme_host = MME_HOST, mme_ip = MME_IP,
                                  hss_host = HSS_HOST, hss_ip = HSS_IP,
                                  spgw_host = SPGW_HOST, spgw_ip = SPGW_IP,
                                  s11_interface = S11_INTERFACE)

        configurator.configure(config)

        mme_fd_config = self.getContent(self.mme_fd_config)
        self.assertEqual(len(mme_fd_config.splitlines()), 3)
        self.assertIn('%s = "%s"' % (IDENTITY, MME_HOST), mme_fd_config)
        self.assertIn('%s = "%s"' % (REALM, REALM_VALUE), mme_fd_config)
        self.assertIn('%s = "%s"' % (CONNECT_PEER, HSS_HOST), mme_fd_config)
        self.assertIn(OTHER_CONFIGS, mme_fd_config)
        self.assertIn('%s = "%s"' % (CONNECT_TO, HSS_IP.split('/')[0]),
                      mme_fd_config)
        self.assertIn('%s = "%s"' % (rEALM, REALM_VALUE), mme_fd_config)

    def testEmptyMessage(self):
        MME_INTF_S11 = 'MME_INTERFACE_NAME_FOR_S11_MME'
        MME_IP_S11 = 'MME_IPV4_ADDRESS_FOR_S11_MME'
        MME_IP_S1 = 'MME_IPV4_ADDRESS_FOR_S1_MME'
        SPGW_IP_S11 = 'SGW_IPV4_ADDRESS_FOR_S11'
        S11_INTERFACE = 'lo'
        MME_HOST, MME_IP = 'mme.domain.my', '11.0.0.1'
        HSS_HOST, HSS_IP = 'hss.domain.my', '12.0.0.1'
        SPGW_HOST, SPGW_IP = 'spgw.domain.my', '10.0.0.4/24'
        CUSTOM_H, CUSTOM_IP = 'custom_host', '11.11.11.11'
        self.writeContent('%s = "%s"\n' % (MME_INTF_S11, S11_INTERFACE), self.mme_config)
        self.writeContent('%s = "%s"\n' % (MME_IP_S11, MME_IP), self.mme_config)
        self.writeContent('%s = "%s"\n' % (MME_IP_S1, MME_IP), self.mme_config)
        self.writeContent('%s = "%s"\n' % (SPGW_IP_S11, SPGW_IP), self.mme_config)

        self.writeContent('%s %s\n' % (MME_IP, MME_HOST), self.host_file)
        self.writeContent('%s %s\n' % (HSS_IP, HSS_HOST), self.host_file)
        self.writeContent('%s %s\n' % (CUSTOM_IP, CUSTOM_H), self.host_file)

        configurator = mme_p.MME_Configurator(self.mme_config,
                                              self.mme_fd_config,
                                              self.host_file)

        config = mme_p.MME_Config()

        configurator.configure(config)

        mme_config = self.getContent(self.mme_config)
        self.assertEqual(len(mme_config.splitlines()), 4)
        self.assertIn('%s = "%s"' % (MME_INTF_S11, S11_INTERFACE), mme_config)
        self.assertIn('%s = "%s"' % (MME_IP_S11, MME_IP), mme_config)
        self.assertIn('%s = "%s"' % (MME_IP_S1, MME_IP), mme_config)
        self.assertIn('%s = "%s"' % (SPGW_IP_S11, SPGW_IP), mme_config)

        host_file_content = self.getContent(self.host_file)
        self.assertEqual(len(host_file_content.splitlines()), 3)
        self.assertIn('%s %s' % (MME_IP, MME_HOST), host_file_content)
        self.assertIn('%s %s' % (HSS_IP, HSS_HOST), host_file_content)
        self.assertIn('%s %s' % (CUSTOM_IP, CUSTOM_H), host_file_content)
