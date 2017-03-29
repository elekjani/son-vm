from son.client.protocol import ClientFactory
from twisted.internet import reactor

import argparse
import logging
import sys

class Client(object):

    def __init__(self, hss_mgmt, mme_mgmt, spgw_mgmt,
                 hss_data, mme_data, spgw_data):
        self.hss_mgmt = hss_mgmt
        self.mme_mgmt = mme_mgmt
        self.spgw_mgmt = spgw_mgmt
        self.hss_data = hss_data
        self.mme_data = mme_data
        self.spgw_data = spgw_data
        self._init_configs()
        self.__init__connection()

    def _init_connection(self):
        self.factory = ClientFactory([
            (self.hss_mgmt, self.hss_config),
            (self.mme_mgmt, self.mme_config),
            (self.spgw_mgmt, self.spgw_config)
        ])

    def _init_configs(self):
        self.hosts = {
            'hss': {
                'host_name': 'hss.openair4G.eur',
                'ip': self.hss_data
            },
            'mme': {
                'host_name': 'mme.openair4G.eur',
                'ip': self.mme_data
            },
            'spgw': {
                'host_name': 'spgw.openair4G.eur',
                'ip': self.spgw_data
            }
        }

        self.hss_config = {
            'hosts': self.hosts,
            'mysql': {
                'user': 'root',
                'pass': 'hurka'
            }
        }

        self.mme_config = {
            'hosts': self.hosts,
            's11_interface': 'eth0'
        }

        self.spgw_config = {
            'hosts': self.hosts,
            's11_interface': 'eth0',
            's11_ip': self.spgw_data,
            'sgi_interface': 'eth0',
            's1u_ip': self.spgw_data,
        }

    def start(self):
        reactor.run()


def main(argv = sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose','-v', action='store_true', dest='verbose',
                        default=False, help='Verbose')
    args, remaining_argv = parser.parse_known_args(argv)

    configArguments = argparse.ArgumentParser()
    configArguments.add_argument('--hss_mgmt', required=True,
                                 help='Management address for HSS')
    configArguments.add_argument('--hss_data', required=True,
                                 help='Data plane address for HSS')
    configArguments.add_argument('--mme_mgmt', required=True,
                                 help='Management address for MME')
    configArguments.add_argument('--mme_data', required=True,
                                 help='Data plane address for MME')
    configArguments.add_argument('--spgw_mgmt', required=True,
                                 help='Management address for SPGW')
    configArguments.add_argument('--spgw_data', required=True,
                                 help='Data plane address for SPGW')
    configArgs = configArguments.parse_args(remaining_argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info('Got cli parameters:')
    configDict = vars(configArgs)
    for param in configDict:
        logger.info('%s -> %s', param, configDict[param])

    c = Client(hss_mgmt = configArgs.hss_mgmt, hss_data = configArgs.hss_data,
               mme_mgmt = configArgs.mme_mgmt, mme_data = configArgs.mme_data,
               spgw_mgmt = configArgs.spgw_mgmt, spgw_data = configArgs.spgw_data)
    c.start()
