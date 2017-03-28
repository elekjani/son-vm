from son.vmmanager.jsonserver import IJsonProcessor as P
import re
import os
import time
import logging
import sys
import subprocess
import shutil
import tempfile
import threading

REGEX_IPV4_NUMBER = '[0-9]{1,3}'
REGEX_IPV4 = r'\.'.join([REGEX_IPV4_NUMBER] * 4)
REGEX_IPV4_MASK = REGEX_IPV4 + '/[0-9]{1,2}'

class ConfiguratorHelpers(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def write_out(self, content, file_path):
        os_fd, tmp_file = tempfile.mkstemp()
        os.close(os_fd)

        with open(tmp_file, 'w') as f:
            f.write(content)

        backup_path = '%s.%s.back' % (file_path, int(time.time()))
        shutil.copy(file_path, backup_path)
        shutil.copy(tmp_file, file_path)
        shutil.copymode(backup_path, file_path)

        os.remove(tmp_file)

    def sed_it(self, regex, sub):
        self._current_line =  re.sub(regex, r'\1"%s"' % sub, self._current_line)
        return self._current_line

    def ip(self, masked_ip):
        return masked_ip.split('/')[0] if masked_ip is not None else None

    def fail(self, message, *args, **kwords):
        self.logger.error(message, *args)
        return P.Result.fail(message, *args, **kwords)

    def ok(self, message, *args, **kwords):
        self.logger.info(message, *args)
        return P.Result.ok(message, *args, **kwords)

    def warn(self, message, *args, **kwords):
        self.logger.warning(message, *args)
        return P.Result.warn(message, *args, **kwords)


class CommandConfig(object):

    START = 1
    STOP = 2
    RESTART = 3
    STATUS = 4

    def __init__(self, command = None, **kwargs):
        self.command = command
        super(CommandConfig, self).__init__(**kwargs)


class CommandMessageParser(object):

    MSG_COMMAND = 'command'
    MSG_COMMAND_START = 'start'
    MSG_COMMAND_STOP = 'stop'
    MSG_COMMAND_RESTART = 'restart'
    MSG_COMMAND_STATUS = 'status'
    MSG_COMMANDS = {
        MSG_COMMAND_START: CommandConfig.START,
        MSG_COMMAND_STOP: CommandConfig.STOP,
        MSG_COMMAND_RESTART: CommandConfig.RESTART,
        MSG_COMMAND_STATUS: CommandConfig.STATUS
    }

    def __init__(self, json_dict = None):
        self.logger = logging.getLogger(CommandMessageParser.__name__)
        self.msg_dict = json_dict

    def parse(self, command_config = None):
        if command_config is None:
            cc = CommandConfig()
        else:
            cc = command_config

        if self.MSG_COMMAND in self.msg_dict:
            cmd = self.msg_dict[self.MSG_COMMAND]
            if cmd not in self.MSG_COMMANDS.keys():
                self.logger.warning('Got invalid command: %s', cmd)
            else:
                cc.command = self.MSG_COMMANDS[cmd]
            self.logger.info('Got command: %s' % cc.command)

        return cc


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


class HostConfigurator(ConfiguratorHelpers):

    def __init__(self, host_file_path):
        self._host_file_path = host_file_path
        super(HostConfigurator, self).__init__()

    def configure(self, host_config):
        if not os.path.isfile(self._host_file_path):
            return self.fail('Host file is not found at %s',
                             self._host_file_path)

        mme_host, mme_ip = host_config.mme_host, self.ip(host_config.mme_ip)
        hss_host, hss_ip = host_config.hss_host, self.ip(host_config.hss_ip)

        config_mme = False
        if mme_host is not None and mme_ip is not None:
            config_mme = True

        config_hss = False
        if hss_host is not None and hss_ip is not None:
            config_hss = True

        if not config_mme and not config_hss:
            return self.warn('No host name and IP given for HSS amd MME')

        new_content = ""
        with open(self._host_file_path, 'r') as f:
            for line in f:
                self._current_line = line
                if config_mme and (mme_host in line or mme_ip in line):
                    self._current_line = '%s %s\n' % (mme_ip, mme_host)
                    config_mme = False

                if config_hss and (hss_host in line or hss_ip in line):
                    self._current_line = '%s %s\n' % (hss_ip, hss_host)
                    config_hss = False

                new_content += self._current_line

        if config_mme:
            new_content += '%s %s\n' % (mme_ip, mme_host)

        if config_hss:
            new_content += '%s %s\n' % (hss_ip, hss_host)

        self.write_out(new_content, self._host_file_path)

        return self.ok('Host file is configured')


class CertificateConfigurator(ConfiguratorHelpers):

    def __init__(self, cert_exe, certificate_path):
        self.logger = logging.getLogger(CertificateConfigurator.__name__)

        if cert_exe is not None:
            self._executable = os.path.expanduser(cert_exe)
        else:
            self._executable = None

        if certificate_path is not None:
            self._certificate_path = os.path.expanduser(certificate_path) if cert_exe is not None else None
        else:
            self._certificate_path = None

        super(CertificateConfigurator, self).__init__()

    def configure(self, host_name):
        if self._executable is None or self._certificate_path is None:
            return self.warn('No executalbe nor certificate path is given.')

        if not os.path.isfile(self._executable):
            return self.fail('Certificate creator does not exist: %s',
                             self._executable)

        if not os.path.isdir(self._certificate_path):
            return self.fail('Certificate path does not exist: %s',
                             self._certificate_path)

        if host_name is None:
            return self.warn('Unable to configure certificates.'
                             'No host is given.')

        subprocess.check_call([self._executable, self._certificate_path,
                               host_name])

        return self.ok('Certificates are configured')


class Runner(object):

    def __init__(self, executable, log_dir=None, start_shell=False):
        self.logger = logging.getLogger(Runner.__name__)
        self._executable = os.path.expanduser(executable)
        self._task = None
        self._isShell = start_shell
        self._std_contents = {1: "", 2: ""}
        self._log_dir = log_dir

    def start(self):
        if self._task is not None:
            return P.Result.fail('Unable to start task %s, '
                                 'it\'s already started', self._executable)

        self.logger.debug("Starting task %s", self._executable)
        self._task = subprocess.Popen(self._executable,
                                      stdin = subprocess.PIPE,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.PIPE,
                                      shell = self._isShell,
                                      bufsize = 0)

        self.logger.debug("Starting IO threads")
        self._std_contents[1] = ""
        self._std_contents[2] = ""
        self._stdout_thread = threading.Thread(target=self._getOutput,
                                               args=[1, self._log_dir])
        self._stderr_thread = threading.Thread(target=self._getOutput,
                                               args=[2, self._log_dir])
        self._stdout_thread.start()
        self._stderr_thread.start()

        return P.Result.ok('Task %s is started', self._executable)

    def _getOutputAndLogFile(self, std, log_dir):
        log_file = None
        if log_dir is None:
            self.logger.debug('No logging directory is given')
        elif os.path.isdir(log_dir):
            if std == 1:
                file_name = os.path.join(log_dir, "stdout")
                self.logger.debug('Writing stdout in file %s', file_name)
            elif std == 2:
                file_name = os.path.join(log_dir, "stderr")
                self.logger.debug('Writing stderr in file %s', file_name)

            log_file = open(file_name, 'w')
        else:
            self.logger.debug('Logging directory %s is not a valid directory',
                              log_dir)

        if std == 1:
            output = self._task.stdout
        elif std == 2:
            output = self._task.stderr

        return (output, log_file)

    def _getOutput(self, std, log_dir):
        if std not in [1,2]:
            self.logger.warning('Invalid output descriptor: %d', std)
            return

        self.logger.debug('IO thread started for output %d', std)

        output, log_file = self._getOutputAndLogFile(std, log_dir)

        while True:
            try:
                line = output.readline()
            except ValueError:
                break

            decoded_line = line.decode()
            self._std_contents[std] += decoded_line
            if log_file is not None:
                log_file.write(decoded_line)

        self.logger.debug('Output %d has been closed, exiting IO thread.', std)

        if log_file is not None:
            log_file.close()

    def stop(self):
        self.logger.info('Stopping task %s', self._executable)
        if self._task is None:
            return P.Result.warn('Unable to stop task %s, it\'s not started',
                                 self._executable)

        self.logger.debug('Killing task')
        if self.isRunning():
            if 'win' in sys.platform:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self._task.pid)])
            elif 'linux' in sys.platform:
                subprocess.call(['kill', '-9', str(self._task.pid)])
            else:
                self._task.kill()

        self.logger.debug('Closing task\'s standard IOs')
        self._task.stdin.close()
        self._task.stdout.close()
        self._task.stderr.close()

        self.logger.debug('Waiting task to stop')
        self._task.wait()
        self._task = None

        self.logger.debug('Waiting standard IO threads to stop')
        self._stderr_thread.join()
        self._stdout_thread.join()

        return P.Result.ok('Task %s is stopped', self._executable)

    def restart(self):
        if self._task is None:
            self.start()
        else:
            self.stop()
            self.start()

    def getOutput(self, stderr=False):
        if stderr:
            return self._std_contents[2]
        else:
            return self._std_contents[1]

    def isRunning(self):
        if self._task is None:
            return False

        returncode = self._task.poll()
        if returncode is None:
            return True
        else:
            return False

    def getReturnCode(self):
        return self._task.poll()


