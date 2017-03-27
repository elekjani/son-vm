from son.vmmanager.jsonserver import IJsonProcessor as P
from son.vmmanager.processors import utils

import logging
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


class HSS_Configurator(utils.ConfiguratorHelpers):

    REGEX_MYSQL_USER = '(.*)"@MYSQL_user@"'
    REGEX_MYSQL_PASS = '(.*)"@MYSQL_pass@"'

    def __init__(self, config_path, host_file_path,
                 cert_exe = None, cert_path = None):
        self._hss_config_path = config_path
        self._host_configurator = utils.HostConfigurator(host_file_path)
        self._cert_configurator = utils.CertificateConfigurator(cert_exe,
                                                                cert_path)
        super(HSS_Configurator, self).__init__()

    def configure(self, hss_config):
        hss_result = self._configure_hss(hss_config)
        host_result = self._host_configurator.configure(hss_config)
        cert_result = self._cert_configurator.configure(hss_config.hss_host)

        results = [hss_result, host_result, cert_result]

        if P.Result.FAILED in [r.status for r in results]:
            return self.fail('HSS configuration failed',
                                 hss=hss_result.message,
                                 host_file=host_result.message,
                                 cert=cert_result.message)

        if P.Result.WARNING in [r.status for r in results]:
            return self.warn('HSS configuration was not complete',
                                 hss=hss_result.message,
                                 host_file=host_result.message,
                                 cert=cert_result.message)

        return self.ok('HSS is fully configured')

    def _configure_hss(self, hss_config):
        if not os.path.isfile(self._hss_config_path):
            return self.fail('HSS config file is not found at %s',
                             self._hss_config_path)

        user = hss_config.mysql_user
        password = hss_config.mysql_pass

        if user is None or password is None:
            return self.warn('Unable to configure HSS '
                             'no MySQL user and password provided')

        new_content = ""
        with open(self._hss_config_path) as f:
            for line in f:
                self._current_line  = line

                self.sed_it(self.REGEX_MYSQL_USER, user)
                self.sed_it(self.REGEX_MYSQL_PASS, password)

                new_content += self._current_line

        self.write_out(new_content, self._hss_config_path)

        return self.ok('HSS is configured')


class HSS_Processor(P):

    HSS_CONFIG_PATH = '/usr/local/etc/oai/hss.conf'
    HOST_FILE_PATH = '/etc/hosts'
    HSS_CERTIFICATE_EXECUTABLE = '~/openair-cn/SCRIPTS/check_hss_s6a_certificate'
    HSS_CERTIFICATE_PATH = '/usr/local/etc/oai/freeDiameter'
    HSS_EXECUTABLE = '~/openair-cn/SCRIPTS/run_hss'

    def __init__(self, hss_config_path = HSS_CONFIG_PATH,
                 hss_freediameter_config_path = HSS_CONFIG_PATH,
                 hss_certificate_exe = HSS_CERTIFICATE_EXECUTABLE,
                 hss_certificate_path = HSS_CERTIFICATE_PATH,
                 host_file_path = HOST_FILE_PATH):
        self.logger = logging.getLogger(HSS_Processor.__name__)

        self._configurator = HSS_Configurator(config_path = hss_config_path,
                                              host_file_path = host_file_path,
                                              cert_exe = hss_certificate_exe,
                                              cert_path = hss_certificate_path)
        self._runner = utils.Runner(self.HSS_EXECUTABLE)


    def process(self, json_dict):
        parser = HSS_MessageParser(json_dict)
        hss_config = parser.parse()

        config_result = self._configurator.configure(hss_config = hss_config)
        if config_result.status == P.Result.FAILED:
            return P.Result.fail('HSS configuration is failed, '
                                 'it will be not executed',
                                 **config_result.args)

        return self._execute_command(hss_config)

    def _execute_command(self, hss_config):
        if hss_config.command == utils.CommandConfig.START:
            return self._runner.start()
        elif hss_config.command == utils.CommandConfig.STOP:
            return self._runner.stop()
        elif hss_config.command == utils.CommandConfig.RESTART:
            return self._runner.restart()
        elif hss_config.command == utils.CommandConfig.STATUS:
            status = 'Running' if self._runner.isRunning() else 'Stopped'
            stdout = self._runner.getOutput()
            stderr = self._runner.getOutput(stderr=True)
            return P.Result.ok('Status', task_status = status,
                               stderr = stderr, stdout = stdout)
        else:
            return P.Result.fail('Invalid command is given %s',
                                 hss_config.command)

