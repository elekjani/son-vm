from son.vmmanager.jsonserver import IJsonProcessor as P
from son.vmmanager.processors import utils
from son.vmmanager.processors.utils import RE_IPV4_MASK
from son.vmmanager.processors.utils import RE_ASSIGNMENT, RE_NAME

import tempfile
import logging
import re
import os

class SPGW_MessageParser(object):

    #Interface to the "Internet"
    MSG_IP_SGI = 'sgi_ip'
    #SAP IP to the UE
    MSG_IP_S1U = 's1u_ip'

    def __init__(self, json_dict):
        self.logger = logging.getLogger(SPGW_MessageParser.__name__)
        self.host_parser = utils.HostMessageParser(json_dict)
        self.command_parser = utils.CommandMessageParser(json_dict)
        self.msg_dict = json_dict

    def parse(self):
        sc = SPGW_Config()

        if self.MSG_IP_SGI in self.msg_dict:
            sc.sgi_ip = self.msg_dict[self.MSG_IP_SGI]
            self.logger.info('Got SGI INTERFACE coniguration: '
                             '%s' % sc.sgi_ip)

        if self.MSG_IP_S1U in self.msg_dict:
            sc.s1u_ip = self.msg_dict[self.MSG_IP_S1U]
            self.logger.info('Got S1U IP coniguration: '
                             '%s' % sc.s1u_ip)

        self.host_parser.parse(sc)
        self.command_parser.parse(sc)

        return sc


class SPGW_Config(utils.CommandConfig, utils.HostConfig):

    def __init__(self, sgi_ip = None, s1u_ip = None, **kwargs):
        self.sgi_ip = sgi_ip
        self.s1u_ip = s1u_ip
        super(self.__class__, self).__init__(**kwargs)


class SPGW_Configurator(utils.ConfiguratorHelpers):

    RE_S11_INTERFACE = RE_ASSIGNMENT('SGW_INTERFACE_NAME_FOR_S11', RE_NAME)
    RE_S11_IP = RE_ASSIGNMENT('SGW_IPV4_ADDRESS_FOR_S11', RE_IPV4_MASK)
    RE_SGI_INTERFACE = RE_ASSIGNMENT('PGW_INTERFACE_NAME_FOR_SGI', RE_NAME)
    RE_S1U_IP = RE_ASSIGNMENT('SGW_IPV4_ADDRESS_FOR_S1U_S12_S4_UP', RE_IPV4_MASK)
    RE_PGW_MASQ = RE_ASSIGNMENT('PGW_MASQUERADE_SGI', 'no')

    def __init__(self, config_path):
        self._spgw_config_path = config_path
        super(SPGW_Configurator, self).__init__()

    def configure(self, spgw_config):
        if not os.path.isfile(self._spgw_config_path):
            return self.fail('SPGW config file is not found at %s',
                             self._spgw_config_path)

        s11_intf = self.getInterfacesName(spgw_config.spgw_ip)
        s11_ip = spgw_config.spgw_ip
        sgi_ip, s1u_ip = spgw_config.sgi_ip, spgw_config.s1u_ip
        sgi_intf = self.getInterfacesName(sgi_ip)

        if s11_intf is None and s11_ip is None \
                and sgi_intf is None and s1u_ip is None:
            return self.warn('No SPGW configuration is privded')

        new_content = ""
        with open(self._spgw_config_path) as f:
            for line in f:
                self._current_line  = line

                if s11_intf is not None:
                    self.sed_it(self.RE_S11_INTERFACE, s11_intf)
                if s11_ip  is not None:
                    self.sed_it(self.RE_S11_IP, s11_ip)
                if sgi_intf is not None:
                    self.sed_it(self.RE_SGI_INTERFACE, sgi_intf)
                if s1u_ip is not None:
                    self.sed_it(self.RE_S1U_IP, s1u_ip)

                self.sed_it(self.RE_PGW_MASQ, 'yes')

                new_content += self._current_line

        self.write_out(new_content, self._spgw_config_path)

        return self.ok('SPGW is configured')


class SPGW_Processor(P):

    SPGW_CONFIG_PATH = '/usr/local/etc/oai/spgw.conf'
    SPGW_EXECUTABLE = '~/openair-cn/SCRIPTS/run_spgw'

    def __init__(self, spgw_config_path = SPGW_CONFIG_PATH):
        self.logger = logging.getLogger(SPGW_Processor.__name__)

        self._configurator = SPGW_Configurator(config_path = spgw_config_path)
        self._log_dir = tempfile.TemporaryDirectory(prefix='spgw.processor')
        self._log_dir_name = self._log_dir.name
        self._runner = utils.Runner(self.SPGW_EXECUTABLE, log_dir = self._log_dir_name)

    def process(self, json_dict):
        parser = SPGW_MessageParser(json_dict)
        spgw_config = parser.parse()

        config_result = self._configurator.configure(spgw_config = spgw_config)
        if config_result.status == P.Result.FAILED:
            return P.Result.fail('SPGW configuration is failed, '
                                 'it will be not exectued',
                                 **config_result.args)

        return self._execute_command(spgw_config)

    def _execute_command(self, spgw_config):
        if spgw_config.command == utils.CommandConfig.START:
            return self._runner.start()
        elif spgw_config.command == utils.CommandConfig.STOP:
            return self._runner.stop()
        elif spgw_config.command == utils.CommandConfig.RESTART:
            return self._runner.restart()
        elif spgw_config.command == utils.CommandConfig.STATUS:
            status = 'Running' if self._runner.isRunning() else 'Stopped'
            stdout = self._runner.getOutput()
            stderr = self._runner.getOutput(stderr=True)
            return P.Result.ok('Status', task_status = status,
                               stderr = stderr, stdout = stdout)
        elif spgw_config.command is None:
            return P.Result.warn('No command is given')
        else:
            return P.Result.fail('Invalid command is given')

