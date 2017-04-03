from son.vmmanager.jsonserver import IJsonProcessor as P
from son.vmmanager.processors import utils
from son.vmmanager.processors.utils import RE_ASSIGNMENT, RE_NAME

import pymysql.cursors
import tempfile
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

    RE_MYSQL_USER = '(.*)"@MYSQL_user@"'
    RE_MYSQL_PASS = '(.*)"@MYSQL_pass@"'

    RE_IDENTITY = RE_ASSIGNMENT('^Identity', RE_NAME)
    RE_REALM = RE_ASSIGNMENT('[Rr]ealm', RE_NAME)

    MYSQL_HOST = 'localhost'
    MYSQL_DB = 'oai_db'
    MYSQL_MME_TABLE = 'mmeidentity'
    MYSQL_MME_HOST_COLUMN = 'mmehost'
    MYSQL_MME_REALM_COLUMN = 'mmerealm'
    MYSQL_MME_UE_REACH_COLUMN = 'UE-Reachability'

    MYSQL_INSERT = 'INSERT INTO `%s` (`%s`, `%s`, `%s`) VALUE (%%s, %%s, %%s)'
    MYSQL_INSERT = MYSQL_INSERT % (MYSQL_MME_TABLE,
                                   MYSQL_MME_HOST_COLUMN,
                                   MYSQL_MME_REALM_COLUMN,
                                   MYSQL_MME_UE_REACH_COLUMN)

    MYSQL_SELECT = 'SELECT * FROM `%s` WHERE `%s`=%%s'
    MYSQL_SELECT = MYSQL_SELECT % (MYSQL_MME_TABLE,
                                   MYSQL_MME_HOST_COLUMN)

    MYSQL_DELETE = 'DELETE * FROM `%s` WHERE `%s`=%%s'
    MYSQL_DELETE = MYSQL_DELETE % (MYSQL_MME_TABLE,
                                   MYSQL_MME_HOST_COLUMN)

    def __init__(self, config_path, fd_config_path, host_file_path,
                 cert_exe = None, cert_path = None):
        self._hss_config_path = config_path
        self._hss_fd_config_path = fd_config_path
        self._host_configurator = utils.HostConfigurator(host_file_path)
        self._cert_configurator = utils.CertificateConfigurator(cert_exe,
                                                                cert_path)
        super(HSS_Configurator, self).__init__()

    def configure(self, hss_config):
        hss_result = self._configure_hss(hss_config)
        hss_fd_result = self._configure_hss_freediameter(hss_config)
        mysql_result = self._configure_mysql_mme(hss_config)
        host_result = self._host_configurator.configure(hss_config)
        cert_result = self._cert_configurator.configure(hss_config.hss_host)

        results = [hss_result, host_result, hss_fd_result,
                   mysql_result, cert_result]

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

    def _configure_hss_freediameter(self, hss_config):
        if not os.path.isfile(self._hss_fd_config_path):
            return self.fail('HSS freediameter config file is not found at '
                             '%s', self._hss_fd_config_path)

        hss_host = hss_config.hss_host
        realm = '.'.join(hss_host.split('.')[1:]) if hss_host is not None else None

        if hss_host is None and realm is None:
            return self.warn('No HSS freediameter configuration is privded')

        new_content = ""
        with open(self._hss_fd_config_path) as f:
            for line in f:
                self._current_line = line

                if hss_host is not None:
                    self.sed_it(self.RE_IDENTITY, hss_host)

                if realm is not None:
                    self.sed_it(self.RE_REALM, realm)

                new_content += self._current_line

        self.write_out(new_content, self._hss_fd_config_path)

        return self.ok('HSS freediameter is configured')

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

                self.sed_it(self.RE_MYSQL_USER, user)
                self.sed_it(self.RE_MYSQL_PASS, password)

                new_content += self._current_line

        self.write_out(new_content, self._hss_config_path)

        return self.ok('HSS is configured')

    def _configure_mysql_mme(self, hss_config):
        user = hss_config.mysql_user
        password = hss_config.mysql_pass

        if user is None or password is None:
            return self.warn('Unable to configure MySQL '
                             'no user and password provided')

        mme_host = hss_config.mme_host
        realm = '.'.join(mme_host.split('.')[1:]) if mme_host is not None else None

        if mme_host is None and realm is None:
            return self.warn('No HSS host and realm is provided')

        connection = None
        try:
            connection = self._db_get_mysql_connection(user, password)
            self._db_clear_database(connection, mme_host)
            self._db_add_mme_host(connection, mme_host, realm)
        except Exception as e:
            return self.fail('Failed to add MME to HSS database: %s', e)
        finally:
            if connection is not None:
                connection.close()

        return self.ok('MME added to HSS database')

    def _db_get_mysql_connection(self, user, password):
        try:
            connection = pymysql.connect(host=self.MYSQL_HOST,
                                        db=self.MYSQL_DB,
                                        user=user,
                                        password=password,
                                        cursorclass=pymysql.cursors.DictCursor)
        except pymysql.err.OperationalError as e:
            raise Exception('Unable to connect ot MySQL', e)

        return connection

    def _db_clear_database(self, connection,  mme_host):
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.MYSQL_SELECT, (mme_host))
                if cursor.rowcount > 0:
                    cursor.execute(self.MYSQL_DELETE, (mme_host))
                    cursor.commit()
        except Exception as e:
            raise Exception('Unable to clear MME from MySQL', e)

    def _db_add_mme_host(self, connection, mme_host, realm):
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.MYSQL_INSERT, (mme_host, realm, 0))
            connection.commit()

            with connection.cursor() as cursor:
                cursor.execute(self.MYSQL_SELECT, (mme_host))
                if cursor.rowcount is not 1:
                    return self.fail('Unable to add MME into MySQL')

                self.logger.debug('MME added to HSS database: %s',
                                  cursor.fetchone())
        except Exception as e:
            raise Exception('Unable to add MME into MySQL', e)


class HSS_Processor(P):

    HSS_FREEDIAMETER_CONFIG_PATH = '/usr/local/etc/oai/freeDiameter/hss_fd.conf'
    HSS_CONFIG_PATH = '/usr/local/etc/oai/hss.conf'
    HOST_FILE_PATH = '/etc/hosts'
    HSS_CERTIFICATE_EXECUTABLE = '~/openair-cn/SCRIPTS/check_hss_s6a_certificate'
    HSS_CERTIFICATE_PATH = '/usr/local/etc/oai/freeDiameter'
    HSS_EXECUTABLE = '~/openair-cn/SCRIPTS/run_hss'

    def __init__(self, hss_config_path = HSS_CONFIG_PATH,
                 hss_freediameter_config_path = HSS_FREEDIAMETER_CONFIG_PATH,
                 hss_certificate_exe = HSS_CERTIFICATE_EXECUTABLE,
                 hss_certificate_path = HSS_CERTIFICATE_PATH,
                 host_file_path = HOST_FILE_PATH):
        self.logger = logging.getLogger(HSS_Processor.__name__)

        self._configurator = HSS_Configurator(hss_config_path,
                                              hss_freediameter_config_path,
                                              host_file_path,
                                              hss_certificate_exe,
                                              hss_certificate_path)
        self._log_dir = tempfile.TemporaryDirectory(prefix='hss.processor')
        self._log_dir_name = self._log_dir.name
        self._runner = utils.Runner(self.HSS_EXECUTABLE,
                                    log_dir=self._log_dir_name)

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
        elif hss_config.command is None:
            return P.Result.warn('No command is given')
        else:
            return P.Result.fail('Invalid command is given %s',
                                 hss_config.command)

