from son.vmmanager.jsonserver import IJsonProcessor
from son.vmmanager.processors import utils

import subprocess
import logging
import tempfile
import shutil
import time
import re
import os

class HSS_MessageParser(object):

    MSG_MYSQL = 'mysql'
    MSG_MYSQL_PASS = 'pass'
    MSG_MYSQL_USER = 'user'

    def __init__(self, json_dict):
        self.logger = logging.getLogger(HSS_MessageParser.__name__)
        self.host_parser = utils.HostMessageParser(json_dict)
        self.command_parser = utils.CommandMessageParser(json_dict)
        self.msg_dict = json_dict

    def parse(self):
        hc = HSS_Config()

        if self.MSG_MYSQL in self.msg_dict:
            mysql = self.msg_dict[self.MSG_MYSQL]
            if self.MSG_MYSQL_USER in mysql and self.MSG_MYSQL_PASS in mysql:
                hc.mysql_user = mysql[self.MSG_MYSQL_USER]
                hc.mysql_pass = mysql[self.MSG_MYSQL_PASS]
                self.logger.info('Got MYSQL credentials: '
                                 '%s - %s', hc.mysql_user, hc.mysql_pass)
            else:
                self.logger.warn('Got incomplete MYSQL creadentials')

        self.host_parser.parse(hc)
        self.command_parser.parse(hc)

        return hc


class HSS_Config(utils.HostConfig, utils.CommandConfig):

    def __init__(self, mysql_user = None, mysql_pass = None, **kwargs):
        self.mysql_user = mysql_user
        self.mysql_pass = mysql_pass
        super(self.__class__, self).__init__(**kwargs)


class HSS_Configurator(utils.HostConfigurator):

    REGEX_MYSQL_USER = '@MYSQL_user@'
    REGEX_MYSQL_PASS = '@MYSQL_pass@'

    def __init__(self, config_path, *args, **kwargs):
        self.logger = logging.getLogger(HSS_Configurator.__name__)
        self._hss_config_path = config_path
        super(self.__class__, self).__init__(*args, **kwargs)

    def configure(self, hss_config):
        self._configure_hss(hss_config)
        super(self.__class__, self).configure(hss_config)

    def _configure_hss(self, hss_config):
        if not os.path.isfile(self._hss_config_path):
            self.logger.warning('MME config file is not found at '
                             '%s' % self._hss_config_path)
            return

        user = hss_config.mysql_user
        password = hss_config.mysql_pass

        if user is None or password is None:
            return

        new_content = ""
        with open(self._hss_config_path) as f:
            for line in f:
                self._current_line  = line

                self._sed_it(self.REGEX_MYSQL_USER, user)
                self._sed_it(self.REGEX_MYSQL_PASS, password)

                new_content += self._current_line

        self._write_out(new_content, self._hss_config_path)

    def _sed_it(self, regex, sub):
        self._current_line =  re.sub(regex, sub, self._current_line)
        return self._current_line

    def _ip(self, masked_ip):
        return masked_ip.split('/')[0] if masked_ip is not None else None
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


class HSS_Runner(utils.Runner):

    EXECUTABLE = '~/openair-cn/SCRIPTS/run_hss'

    def __init__(self, executable = EXECUTABLE):
        super(self.__class__, self).__init__(executable)


class HSS_Processor(IJsonProcessor):

    HSS_CONFIG_PATH = '/usr/local/etc/oai/hss.conf'
    HOST_FILE_PATH = '/etc/hosts'

    def __init__(self, hss_config_path = HSS_CONFIG_PATH,
                 hss_freediameter_config_path = HSS_CONFIG_PATH,
                 host_file_path = HOST_FILE_PATH):
        self.logger = logging.getLogger(HSS_Processor.__name__)

        self._configurator = HSS_Configurator(hss_config_path, host_file_path)
        self._runner = HSS_Runner()


    def process(self, json_dict):
        parser = HSS_MessageParser(json_dict)
        hss_config = parser.parse()
        self._configurator.configure(hss_config)
        self._execute_command(hss_config)

    def _execute_command(self, hss_config):
        if hss_config.command == 'start':
            self._runner.start()
        elif hss_config.command == 'stop':
            self._runner.stop()
        elif hss_config.command == 'restart':
            self._runner.restart()

