from son.client.protocol import ClientFactory
from twisted.internet.protocol import Protocol, ClientFactory
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

    def _init_connection(self):
        self.factory = ClientFactory([
            (self.hss_mgmt, self.hss_config),
            (self.mme_mgmt, self.mme_config),
            (self.spgw_mgmt, self.spgw_config),
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
    parser.add_argument('--hss_mgmt', required=True,
                        help='Management address for HSS')
    parser.add_argument('--hss_data', required=True,
                        help='Data plane address for HSS')
    parser.add_argument('--mme_mgmt', required=True,
                        help='Management address for MME')
    parser.add_argument('--mme_data', required=True,
                        help='Data plane address for MME')
    parser.add_argument('--spgw_mgmt', required=True,
                        help='Management address for SPGW')
    parser.add_argument('--spgw_data', required=True,
                        help='Data plane address for SPGW')
    parser.add_argument('--verbose','-v', action='store_true', dest='verbose',
                        default=False, help='Verbose')
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    c = Client(hss_mgmt = args.hss_mgmt, hss_data = args.hss_data,
               mme_mgmt = args.mme_mgmt, mme_data = args.mme_data,
               spgw_mgmt = args.spgw_mgmt, spgw_data = args.spgw_data)
    c.start()
