"""
    Initializes the contract scanners
"""

import os
from scanwrapper import BSCContractScanner, EthContractScanner
import argparse
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(description=("Contract parser for XScan apis (etherscan, bscscan, etc)"
                                              "\n*If an API key is not provided, then the .env file will "
                                              "be checked. If there is no API key in the .env file, the"
                                              "program will exit\n"
                                              "\nUsage:\n-python contractscanner.py 0x375223d6ed2b7e08bf7fc552d72eba403e4b9406"
                                              "\n-python contractscanner.py 0x375223d6ed2b7e08bf7fc552d72eba403e4b9406 --chains bsc"
                                              "\n-python contractscanner.py 0x375223d6ed2b7e08bf7fc552d72eba403e4b9406 --chains bsc -bk YOUR_BSCSCAN_API_KEY"),formatter_class=RawTextHelpFormatter)
parser.add_argument('address', type=str, help="The address to collect the source code of")
parser.add_argument('-bk', '--bscKey', type=str, help="API Key to use for BSC Scan.")
parser.add_argument('-ek', '--ethKey', type=str, help="API Key to use for Eth Scan")
parser.add_argument('-c', "--chain", type=str, help="Chain to run analysis on \n Supported options:\n-eth\n-bsc\n", required=True)

args = parser.parse_args()

if args.chain == "bsc":
    bscApiKey = bscApiKey = os.getenv("bscApiKey") if args.bscKey == None else args.bscKey
    scanner = BSCContractScanner(bscApiKey)
    print(scanner.get_contract(args.address))

if args.chain == "eth":
    ethApiKey = ethApiKey = os.getenv("ethApiKey") if args.ethKey == None else args.ethKey
    scanner = EthContractScanner(ethApiKey)
    print(scanner.get_contract(args.address))




