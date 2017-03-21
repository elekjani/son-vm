import re
import os
import logging
import subprocess

REGEX_IPV4_NUMBER = '[0-9]{1,3}'
REGEX_IPV4 = r'\.'.join([REGEX_IPV4_NUMBER] * 4)
REGEX_IPV4_MASK = REGEX_IPV4 + '/[0-9]{1,2}'


class CommandMessageParser(object):

    MSG_COMMAND = 'command'
    MSG_COMMAND_START = 'start'
    MSG_COMMAND_STOP = 'stop'
    MSG_COMMAND_RESTART = 'restart'
    MSG_MESSAGES = [MSG_COMMAND_START, MSG_COMMAND_STOP, MSG_COMMAND_RESTART]

    def __init__(self, json_dict = None):
        self.logger = logging.getLogger(CommandMessageParser.__name__)
        self.msg_dict = json_dict

    def parse(self, command_config = None):
        if command_config is None:
            cc = CommandConfg()
        else:
            cc = command_config

        if self.MSG_COMMAND in self.msg_dict:
            cmd = self.msg_dict[self.MSG_COMMAND]
            if cmd not in self.MSG_MESSAGES:
                self.logger.warning('Got invalid command: %s', cmd)
            else:
                cc.command = cmd
            self.logger.info('Got command: %s' % cc.command)

        return cc


class CommandConfig(object):

    def __init__(self, command = None, **kwargs):
        self.command = command
        super(CommandConfig, self).__init__(**kwargs)


class HostMessageParser(object):

    MSG_HOSTS = 'hosts'
    MSG_HOST_NAME = 'host_name'
    MSG_IP_ADDRESS = 'ip'
    MSG_MME_HOST = 'mme'
    MSG_HSS_HOST = 'hss'
    MSG_SPGW_HOST = 'spgw'

    def __init__(self, json_dict = None):
        self.logger = logging.getLogger(HostMessageParser.__name__)
        self.msg_dict = json_dict

    def _parse_host(self, host_dict):
        if self.MSG_HOST_NAME not in host_dict:
            self.logger.warning('Host configuration is not complete.')
            self.logger.warning('\tNo hostname is given '
                             '(key: %s)' % self.MSG_HOST_NAME)
            return None, None

        if self.MSG_IP_ADDRESS not in host_dict:
            self.logger.warning('Host configuration is not complete.')
            self.logger.warning('\tNo IP address is given '
                             '(key: %s)' % self.MSG_IP_ADDRESS)
            return None, None

        host, ip = host_dict[self.MSG_HOST_NAME], host_dict[self.MSG_IP_ADDRESS]
        if re.match(REGEX_IPV4_MASK, ip) is None:
            self.logger.warning('Got invalid IP address %s', ip)
            host, ip = None, None

        return host, ip

    def parse(self, host_config = None):
        if host_config is None:
            hc = HostConfig()
        else:
            hc = host_config

        if self.MSG_HOSTS in self.msg_dict:

            hosts_dict  = self.msg_dict[self.MSG_HOSTS]

            if self.MSG_MME_HOST in hosts_dict:
                hc.mme_host, hc.mme_ip = self._parse_host(hosts_dict[self.MSG_MME_HOST])
                self.logger.info('Got host configuration for MME: '
                                 '%s (%s)' % (hc.mme_host, hc.mme_ip))

            if self.MSG_HSS_HOST in hosts_dict:
                hc.hss_host, hc.hss_ip = self._parse_host(hosts_dict[self.MSG_HSS_HOST])
                self.logger.info('Got host configuration for HSS: '
                                 '%s (%s)' % (hc.hss_host, hc.hss_ip))

            if self.MSG_SPGW_HOST in hosts_dict:
                hc.spgw_host, hc.spgw_ip = self._parse_host(hosts_dict[self.MSG_SPGW_HOST])
                self.logger.info('Got host configuration for SPGW: '
                                 '%s (%s)' % (hc.spgw_host, hc.spgw_ip))

        return hc


class HostConfig(object):

    def __init__(self, mme_host = None, mme_ip = None,
                 hss_host = None, hss_ip = None,
                 spgw_host = None, spgw_ip = None, **kwargs):
        self.mme_host = mme_host
        self.mme_ip = mme_ip
        self.hss_host = hss_host
        self.hss_ip = hss_ip
        self.spgw_host = spgw_host
        self.spgw_ip = spgw_ip
        super(HostConfig, self).__init__(**kwargs)


class HostConfigurator(object):

    def __init__(self, host_file_path):
        self._host_file_path = host_file_path

    def configure(self, host_config):
        self._configure_host_file(host_config)

    def _configure_host_file(self, hss_config):
        if not os.path.isfile(self._host_file_path):
            self.logger.warning('Host file is not found at %s', self._host_file_path)
            return

        mme_host, mme_ip = hss_config.mme_host, self._ip(hss_config.mme_ip)
        hss_host, hss_ip = hss_config.hss_host, self._ip(hss_config.hss_ip)

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
                    self._current_line = '%s %s\n' % (mme_ip, mme_host)
                    config_mme = False

                if config_hss and hss_host in line or hss_ip in line:
                    self._current_line = '%s %s\n' % (hss_ip, hss_host)
                    config_hss = False

                new_content += self._current_line

        if config_mme:
            new_content += '%s %s\n' % (mme_ip, mme_host)

        if config_hss:
            new_content += '%s %s\n' % (hss_ip, hss_host)

        self._write_out(new_content, self._host_file_path)


class Runner(object):

    def __init__(self, executable):
        self.logger = logging.getLogger(Runner.__name__)
        self._executable = executable
        self._task = None

    def start(self):
        if self._task is not None:
            self.logger.warn('Unable to start task MME,'
                             ' it\'s already started')
            return

        self._task = subprocess.Popen(self._executable,
                                      stdin = subprocess.PIPE,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.STDOUT,
                                      bufsize = 4096,
                                      shell = True)

    def stop(self):
        if self._task is None:
            self.logger.warn('Unable to stop task MME,'
                             ' it\'s not started')
            return

        self._task.kill()
        self._task = None

    def restart(self):
        if self._task is None:
            self.start()
        else:
            self.stop()
            self.start()

    def getOutput(self):
        content = ""
        for line in self._task.stdout:
            content += line.decode().replace('\n', '').replace('\r', '')

        return content

    def isRunning(self):
        returncode = self._task.poll()
        if returncode is None:
            return True
        else:
            return False

    def getReturnCode(self):
        return self._task.poll()


