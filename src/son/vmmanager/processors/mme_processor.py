from son.vmmanager.jsonserver import IJsonProcessor
from son.vmmanager.processors import utils
from son.vmmanager.processors.utils import REGEX_IPV4_MASK
from son.vmmanager.processors.utils import REGEX_IPV4

import logging
import re
import os


class MME_MessageParser(object):

    MSG_S11_INTERFACE = 's11_interface'

    def __init__(self, json_dict):
        self.logger = logging.getLogger(MME_MessageParser.__name__)
        self.msg_dict = json_dict
        self.host_parser = utils.HostMessageParser(json_dict)
        self.command_parser = utils.CommandMessageParser(json_dict)

    def parse(self):
        mc = MME_Config()

        if self.MSG_S11_INTERFACE in self.msg_dict:
            mc.s11_interface = self.msg_dict[self.MSG_S11_INTERFACE]
            self.logger.info('Got S11 interface coniguration: '
                             '%s' % mc.s11_interface)

        self.host_parser.parse(mc)
        self.command_parser.parse(mc)

        return mc


class MME_Config(utils.HostConfig, utils.CommandConfig):

    def __init__(self, s11_interface = None, **kwargs):
        self.s11_interface = s11_interface
        super(self.__class__, self).__init__(**kwargs)


class MME_Configurator(utils.ConfiguratorHelpers):

    REGEX_S1_IPV4 = '(MME_IPV4_ADDRESS_FOR_S1_MME += )"%s"' % REGEX_IPV4_MASK
    REGEX_S11_INTERFACE = '(MME_INTERFACE_NAME_FOR_S11_MME += )"[a-z0-9]+"'
    REGEX_S11_IPV4 = '(MME_IPV4_ADDRESS_FOR_S11_MME += )"%s"' % REGEX_IPV4_MASK
    REGEX_SGW_IPV4 = '(SGW_IPV4_ADDRESS_FOR_S11 += )"%s"' % REGEX_IPV4_MASK

    REGEX_IDENTITY = '(^Identity = ).*'
    REGEX_CONNECT_PEER = r'(^ConnectPeer = )"[a-zA-Z\.0-9]+"'
    REGEX_CONNECT_TO = r'(ConnectTo = )"%s"' % REGEX_IPV4
    REGEX_REALM = r'([Rr]ealm = )"[a-zA-Z\.0-9]+"'

    def __init__(self, config_path, fd_config_path, host_file_path,
                 cert_exe = None, cert_path = None):
        self.logger = logging.getLogger(MME_Configurator.__name__)
        self._mme_config_path = config_path
        self._mme_fd_config_path = fd_config_path
        self._host_configurator = utils.HostConfigurator(host_file_path)
        self._cert_configurator = utils.CertificateConfigurator(cert_exe,
                                                                cert_path)

    def configure(self, mme_config):
        self._configure_mme(mme_config)
        self._configure_mme_freediameter(mme_config)
        self._host_configurator.configure(mme_config)
        self._cert_configurator.configure(mme_config.mme_host)

    def _configure_mme_freediameter(self, mme_config):
        if not os.path.isfile(self._mme_fd_config_path):
            self.logger.warning('MME freediameter config file is not found at '
                             '%s' % self._mme_fd_config_path)
            return

        mme_host = mme_config.mme_host
        hss_host = mme_config.hss_host
        hss_ip = mme_config.hss_ip
        hss_ip = self.ip(hss_ip)
        realm = '.'.join(mme_host.split('.')[1:]) if mme_host is not None else None

        new_content = ""
        with open(self._mme_fd_config_path) as f:
            for line in f:
                self._current_line = line

                if mme_host is not None:
                    self.sed_it(self.REGEX_IDENTITY, mme_host)

                if realm is not None:
                    self.sed_it(self.REGEX_REALM, realm)

                if hss_host is not None:
                    self.sed_it(self.REGEX_CONNECT_PEER, hss_host)

                if hss_ip is not None:
                    self.sed_it(self.REGEX_CONNECT_TO, hss_ip)

                new_content += self._current_line

        self.write_out(new_content, self._mme_fd_config_path)

    def _configure_mme(self, mme_config):
        if not os.path.isfile(self._mme_config_path):
            self.logger.warning('MME config file is not found at '
                             '%s' % self._mme_config_path)
            return

        s11_intf = mme_config.s11_interface
        mme_ip = mme_config.mme_ip
        spgw_ip = mme_config.spgw_ip

        new_content = ""
        with open(self._mme_config_path) as f:
            for line in f:
                self._current_line  = line

                if s11_intf is not None:
                    self.sed_it(self.REGEX_S11_INTERFACE, s11_intf)

                if mme_ip is not None:
                    self.sed_it(self.REGEX_S11_IPV4, mme_ip)
                    self.sed_it(self.REGEX_S1_IPV4, mme_ip)

                if spgw_ip is not None:
                    self.sed_it(self.REGEX_SGW_IPV4, spgw_ip)

                new_content += self._current_line

        self.write_out(new_content, self._mme_config_path)


class MME_Processor(IJsonProcessor):

    MME_FREEDIAMETER_CONFIG_PATH = '/usr/local/etc/oai/freeDiameter/mme_fd.conf'
    MME_CONFIG_PATH = '/usr/local/etc/oai/mme.conf'
    HOST_FILE_PATH = '/etc/hosts'
    MME_CERTIFICATE_CREATOR= '~/openair-cn/SCRIPTS/check_mme_s6a_certificate'
    MME_CERTIFICATE_PATH = '/usr/local/etc/oai/freeDiameter/'
    MME_EXECUTABLE = '~/openair-cn/SCRIPTS/run_mme'

    def __init__(self, mme_config_path = MME_CONFIG_PATH,
                 mme_freediameter_config_path = MME_CONFIG_PATH,
                 host_file_path = HOST_FILE_PATH,
                 cert_exe = MME_CERTIFICATE_CREATOR,
                 cert_path = MME_CERTIFICATE_PATH):
        self.logger = logging.getLogger(MME_Processor.__name__)

        self._configurator = MME_Configurator(mme_config_path,
                                              mme_freediameter_config_path,
                                              host_file_path,
                                              cert_exe, cert_path)
        self._runner = utils.Runner(self.MME_EXECUTABLE)

    def process(self, json_dict):
        parser = MME_MessageParser(json_dict)
        mme_config = parser.parse()
        self._configurator.configure(mme_config)
        self._execute_command(mme_config)

    def _execute_command(self, mme_config):
        if mme_config.command == 'start':
            self._runner.start()
        elif mme_config.command == 'stop':
            self._runner.stop()
        elif mme_config.command == 'restart':
            self._runner.restart()

