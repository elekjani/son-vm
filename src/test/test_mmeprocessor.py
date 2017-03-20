import son.vmmanager.processors.mme_processor as mme_p

import unittest
import logging

logging.basicConfig(level=logging.DEBUG)

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

