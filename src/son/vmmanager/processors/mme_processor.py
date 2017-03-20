from son.vmmanager.jsonserver import IJsonProcessor

import logging
import tempfile
import shutil
import time
import re
import os

REGEX_IPV4_NUMBER = '[0-9]{1,3}'
REGEX_IPV4 = r'\.'.join([REGEX_IPV4_NUMBER] * 4)
REGEX_IPV4_MASK = REGEX_IPV4 + '/[0-9]{1,2}'


class MME_Processor(IJsonProcessor):

    MME_FREEDIAMETER_CONFIG_PATH = '/usr/local/etc/oai/freeDiameter/mme_fd.conf'
    MME_CONFIG_PATH = '/usr/local/etc/oai/mme.conf'
    HOST_FILE_PATH = '/etc/hosts'

    def __init__(self, mme_config_path = None,
                 mme_freediameter_config_path = None,
                 host_file_path = None):
        self.logger = logging.getLogger(MME_Processor.__name__)

        mme_config = self.MME_CONFIG_PATH
        if mme_config_path is not None:
            mme_conf = mme_config_path

        fd_config = self.MME_CONFIG_PATH
        if mme_freediameter_config_path is not None:
            fd_conf = mme_freediameter_config_path

        host_file = self.HOST_FILE_PATH
        if host_file_path is not None:
            host_file = host_file_path

        self._configurator = MME_Configurator(mme_config, fd_config, host_file)
        self._mme_config_path = mme_config_path
        self._mme_fd_config_path = mme_freediameter_config_path
        self._host_file_path = host_file_path

        self._reset_values()

    def process(self, json_dict):
        parser = MME_MessageParser(json_dict)
        mme_config = parser.parse()
        self._configurator.configure(mme_config)
        self._execute_command()
        self._reset_values()

    def _reset_values(self):
        self._mme_host_name = None
        self._mme_address = None
        self._hss_host_name = None
        self._hss_address = None
        self._spgw_host_name = None
        self._spgw_address = None

        self._s11_interface = None

        self._command = None

    def _execute_command(self):
        pass


class MME_MessageParser(object):

    MSG_HOSTS = 'hosts'
    MSG_HOST_NAME = 'host_name'
    MSG_IP_ADDRESS = 'ip'
    MSG_MME_HOST = 'mme'
    MSG_HSS_HOST = 'hss'
    MSG_SPGW_HOST = 'spgw'

    MSG_S11_INTERFACE = 's11_interface'

    MSG_COMMAND = 'command'
    MSG_COMMAND_START = 'start'
    MSG_COMMAND_STOP = 'stop'
    MSG_COMMAND_RESTART = 'restart'
    MSG_MESSAGES = [MSG_COMMAND_START, MSG_COMMAND_STOP, MSG_COMMAND_RESTART]

    def __init__(self, json_dict):
        self.logger = logging.getLogger(MME_MessageParser.__name__)
        self._json_dict = json_dict

    def parse(self):
        mc = MME_Config()

        if self.MSG_HOSTS in self._json_dict:

            hosts_dict  = self._json_dict[self.MSG_HOSTS]

            if self.MSG_MME_HOST in hosts_dict:
                mc.mme_host, mc.mme_ip = self._parse_host(hosts_dict[self.MSG_MME_HOST])
                self.logger.info('Got host configuration for MME: '
                                 '%s (%s)' % (mc.mme_host, mc.mme_ip))

            if self.MSG_HSS_HOST in hosts_dict:
                mc.hss_host, mc.hss_ip = self._parse_host(hosts_dict[self.MSG_HSS_HOST])
                self.logger.info('Got host configuration for HSS: '
                                 '%s (%s)' % (mc.hss_host, mc.hss_ip))

            if self.MSG_SPGW_HOST in hosts_dict:
                mc.spgw_host, mc.spgw_ip = self._parse_host(hosts_dict[self.MSG_SPGW_HOST])
                self.logger.info('Got host configuration for SPGW: '
                                 '%s (%s)' % (mc.spgw_host, mc.spgw_ip))

        if self.MSG_S11_INTERFACE in self._json_dict:
            mc.s11_interface = self._json_dict[self.MSG_S11_INTERFACE]
            self.logger.info('Got S11 interface coniguration: '
                             '%s' % mc.s11_interface)

        if self.MSG_COMMAND in self._json_dict:
            cmd = self._json_dict[self.MSG_COMMAND]
            if cmd not in self.MSG_MESSAGES:
                self.logger.warn('Got invalid command: %s', cmd)
            else:
                mc.command = cmd
            self.logger.info('Got command: %s' % mc.command)


        return mc

    def _parse_host(self, host_dict):
        if self.MSG_HOST_NAME not in host_dict:
            self.logger.warn('Host configuration is not complete.')
            self.logger.warn('\tNo hostname is given '
                             '(key: %s)' % self.MSG_HOST_NAME)
            return None, None

        if self.MSG_IP_ADDRESS not in host_dict:
            self.logger.warn('Host configuration is not complete.')
            self.logger.warn('\tNo IP address is given '
                             '(key: %s)' % self.MSG_IP_ADDRESS)
            return None, None

        host, ip = host_dict[self.MSG_HOST_NAME], host_dict[self.MSG_IP_ADDRESS]
        if re.match(REGEX_IPV4_MASK, ip) is None:
            self.logger.warn('Got invalid IP address %s', ip)
            host, ip = None, None

        return host, ip


class MME_Config(object):

    def __init__(self, mme_host = None, mme_ip = None,
                 hss_host = None, hss_ip = None,
                 spgw_host = None, spgw_ip = None,
                 s11_interface = None, command = None):
        self.mme_host = mme_host
        self.mme_ip = mme_ip
        self.hss_host = hss_host
        self.hss_ip = hss_ip
        self.spgw_host = spgw_host
        self.spgw_ip = spgw_ip
        self.s11_interface = s11_interface
        self.command = command


class MME_Configurator(object):

    REGEX_S1_IPV4 = '(MME_IPV4_ADDRESS_FOR_S1_MME += )"%s"' % REGEX_IPV4_MASK
    REGEX_S11_INTERFACE = '(MME_INTERFACE_NAME_FOR_S11_MME += )"lo"'
    REGEX_S11_IPV4 = '(MME_IPV4_ADDRESS_FOR_S11_MME += )"%s"' % REGEX_IPV4_MASK
    REGEX_SGW_IPV4 = '(SGW_IPV4_ADDRESS_FOR_S11 += )"%s"' % REGEX_IPV4_MASK

    REGEX_IDENTITY = '(^Identity = ).*'
    REGEX_CONNECT_PEER = '(^ConnectPeer = ).*'

    def __init__(self, config_path, fd_config_path, host_file_path):
        self.logger = logging.getLogger(MME_Configurator.__name__)
        self._mme_config_path = config_path
        self._mme_fd_config_path = fd_config_path
        self._host_file_path = host_file_path

    def configure(self, mme_config):
        self._configure_mme(mme_config)
        self._configure_mme_freediamater(mme_config)
        self._configure_host_file(mme_config)

    def _configure_host_file(self, mme_config):
        if not os.path.isfile(self._host_file_path):
            self.logger.warn('Host file is not found at %s', self._host_file_path)
            return

        mme_host, mme_ip = mme_config.mme_host, mme_config.mme_ip
        hss_host, hss_ip = mme_config.hss_host, mme_config.hss_ip

        config_mme = False
        if mme_host is not None and mme_ip is not None:
            config_mme = True

        config_hss = False
        if hss_host is not None and hss_ip is not None:
            config_hss = True

        new_content = ""
        with open(self._host_file_path, 'r') as f:
            for line in f:
                self._current_line = line
                if config_mme and mme_host in line or mme_ip in line:
                    self._sed_it('.*', '%s %s' % (mme_ip, mme_host))
                    config_mme = False

                if config_hss and hss_host in line or hss_ip in line:
                    self._sed_it('.*', '%s %s' % (hss_ip, hss_host))
                    config_hss = False

                new_content += self._current_line

        if config_mme:
            new_content += '%s %s' % (mme_ip, mme_host)

        if config_hss:
            new_content += '%s %s' % (hss_ip, hss_host)

        self._write_out(new_content, self._host_file_path)

    def _configure_mme_freediameter(self, mme_config):
        if not os.path.isfile(self._mme_fd_config_path):
            self.logger.warn('MME freediameter config file is not found at '
                             '%s' % self._mme_fd_config_path)
            return

        mme_host = mme_config.mme_host
        hss_ip = mme_config.hss_ip

        new_content = ""
        with open(self._mme_fd_config_path) as f:
            for line in f:
                self._current_line = line

                if mme_host is not None:
                    self._sed_it(self.REGEX_IDENTITY, mme_host)

                if hss_ip is not None:
                    self._sed_it(self.REGEX_CONNECT_PEER, self.hss_ip)

                new_content += self._current_line

        self._write_out(new_content, self._mme_fd_config_path)

    def _configure_mme(self, mme_config):
        if not os.path.isfile(self._mme_config_path):
            self.logger.warn('MME config file is not found at '
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
                    self._sed_it(self.REGEX_S11_INTERFACE, s11_intf)

                if mme_ip is not None:
                    self._sed_it(self.REGEX_S11_IPV4, mme_ip)
                    self._sed_it(self.REGEX_S1_IPV4, mme_ip)

                if spgw_ip is not None:
                    self._sed_it(self.REGEX_SGW_IPV4, spgw_ip)

                new_content += self._current_line

        self._write_out(new_content, self._mme_config_path)

    def _sed_it(self, regex, sub):
        return re.sub(regex, r'\1"%s"' % sub, self._current_line)

    def _write_out(self, content, file_path):
        os_fd, tmp_file = tempfile.mkstemp()
        os.close(os_fd)

        with open(tmp_file, 'w') as f:
            f.write(content)

        backup_path = '%s.%s.back' % (file_path, int(time.time()))
        shutil.copy(file_path, backup_path)
        shutil.copy(tmp_file, file_path)
        shutil.copymode(backup_path, file_path)

        os.remove(tmp_file)


