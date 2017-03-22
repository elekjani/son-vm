from son.vmmanager.jsonserver import IJsonProcessor
from son.vmmanager.processors import utils

import logging
import re
import os

class SPGW_MessageParser(object):

    MSG_INTERFACE_S11 = 's11_interface'
    MSG_IP_S11 = 's11_ip'
    MSG_INTERFACE_SGI = 'sgi_interface'
    MSG_IP_S1U = 's1u_ip'

    def __init__(self, json_dict):
        self.logger = logging.getLogger(SPGW_MessageParser.__name__)
        self.command_parser = utils.CommandMessageParser(json_dict)
        self.msg_dict = json_dict

    def parse(self):
        sc = SPGW_Config()

        if self.MSG_INTERFACE_S11 in self.msg_dict:
            sc.s11_interface = self.msg_dict[self.MSG_INTERFACE_S11]
            self.logger.info('Got S11 interface coniguration: '
                             '%s' % sc.s11_interface)

        if self.MSG_IP_S11 in self.msg_dict:
            sc.s11_ip = self.msg_dict[self.MSG_IP_S11]
            self.logger.info('Got S11 IP coniguration: '
                             '%s' % sc.s11_ip)

        if self.MSG_INTERFACE_SGI in self.msg_dict:
            sc.sgi_interface = self.msg_dict[self.MSG_INTERFACE_SGI]
            self.logger.info('Got SGI INTERFACE coniguration: '
                             '%s' % sc.sgi_interface)

        if self.MSG_IP_S1U in self.msg_dict:
            sc.s1u_ip = self.msg_dict[self.MSG_IP_S1U]
            self.logger.info('Got S1U IP coniguration: '
                             '%s' % sc.s1u_ip)

        self.command_parser.parse(sc)

        return sc


class SPGW_Config(utils.CommandConfig):

    def __init__(self, s11_interface = None, s11_ip = None,
                 sgi_interface = None, s1u_ip = None, **kwargs):
        self.s11_interface = s11_interface
        self.s11_ip = s11_ip
        self.sgi_interface = sgi_interface
        self.s1u_ip = s1u_ip
        super(self.__class__, self).__init__(**kwargs)


class SPGW_Configurator(utils.ConfiguratorHelpers):

    REGEX_S11_INTERFACE = '(SGW_INTERFACE_NAME_FOR_S11 += )"[a-z0-9]+"'
    REGEX_S11_IP = '(SGW_IPV4_ADDRESS_FOR_S11 += )"%s"' % utils.REGEX_IPV4_MASK
    REGEX_SGI_INTERFACE = '(PGW_INTERFACE_NAME_FOR_SGI += )"[a-z0-9]+"'
    REGEX_S1U_IP = '(SGW_IPV4_ADDRESS_FOR_S1U_S12_S4_UP += )"%s"' % utils.REGEX_IPV4_MASK

    def __init__(self, config_path):
        self.logger = logging.getLogger(SPGW_Configurator.__name__)
        self._spgw_config_path = config_path

    def configure(self, spgw_config):
        if not os.path.isfile(self._spgw_config_path):
            self.logger.warning('SPGW config file is not found at '
                             '%s' % self._spgw_config_path)
            return

        s11_intf, s11_ip = spgw_config.s11_interface, spgw_config.s11_ip
        sgi_intf, s1u_ip = spgw_config.sgi_interface, spgw_config.s1u_ip

        new_content = ""
        with open(self._spgw_config_path) as f:
            for line in f:
                self._current_line  = line

                if s11_intf is not None:
                    self.sed_it(self.REGEX_S11_INTERFACE, s11_intf)
                if s11_ip  is not None:
                    self.sed_it(self.REGEX_S11_IP, s11_ip)
                if sgi_intf is not None:
                    self.sed_it(self.REGEX_SGI_INTERFACE, sgi_intf)
                if s1u_ip is not None:
                    self.sed_it(self.REGEX_S1U_IP, s1u_ip)

                new_content += self._current_line

        self.write_out(new_content, self._spgw_config_path)


class SPGW_Processor(IJsonProcessor):

    SPGW_CONFIG_PATH = '/usr/local/etc/oai/spgw.conf'
    SPGW_EXECUTABLE = '~/openair-cn/SCRIPTS/run_spgw'

    def __init__(self, spgw_config_path = SPGW_CONFIG_PATH):
        self.logger = logging.getLogger(SPGW_Processor.__name__)

        self._configurator = SPGW_Configurator(config_path = spgw_config_path)
        self._runner = utils.Runner(self.SPGW_EXECUTABLE)

    def process(self, json_dict):
        parser = SPGW_MessageParser(json_dict)
        spgw_config = parser.parse()
        self._configurator.configure(spgw_config = spgw_config)
        self._execute_command(spgw_config)

    def _execute_command(self, spgw_config):
        if spgw_config.command == 'start':
            self._runner.start()
        elif spgw_config.command == 'stop':
            self._runner.stop()
        elif spgw_config.command == 'restart':
            self._runner.restart()

