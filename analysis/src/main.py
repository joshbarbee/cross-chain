"""
    Initializes the contract scanners
"""

import os
from scanwrapper import BSCContractScanner, EthContractScanner
import argparse
from argparse import RawTextHelpFormatter
from mgowrapper import MongoFetcher
from transaction import Transaction
from contractstore import ContractStore

parser = argparse.ArgumentParser(description=("Contract parser for XScan apis (etherscan, bscscan, etc)"
                                              "\n*If an API key is not provided, then the .env file will "
                                              "be checked. If there is no API key in the .env file, the"
                                              "program will exit\n"
                                              "\nUsage:\n-python contractscanner.py -tx {TX_HASH}"
                                              "\n-python contractscanner.py --chains bsc -tx {TX_HASH}"
                                              "\n-python contractscanner.py  --chains bsc -bk YOUR_BSCSCAN_API_KEY -tx {TX_HASH}"), formatter_class=RawTextHelpFormatter)
parser.add_argument('-tx', '--transaction', type=str)
parser.add_argument('-bk', '--bscKey', type=str,
                    help="API Key to use for BSC Scan.")
parser.add_argument('-ek', '--ethKey', type=str,
                    help="API Key to use for Eth Scan")
parser.add_argument('-c', "--chain", type=str,
                    help="Chain to run analysis on \n Supported options:\n-eth\n-bsc\n", required=True)

args = parser.parse_args()


if args.chain == "bsc":
    fetch = MongoFetcher("bsc")
    bscApiKey = bscApiKey = os.getenv(
        "bscApiKey") if args.bscKey == None else args.bscKey
    store = ContractStore(BSCContractScanner(bscApiKey))

    if args.transaction != None:
        tx = Transaction(args.transaction, fetch, store)
        print(tx.interacted_functions())
        print(tx)

if args.chain == "eth":
    fetch = MongoFetcher("eth")
    ethApiKey = ethApiKey = os.getenv(
        "ethApiKey") if args.ethKey == None else args.ethKey
    store = ContractStore(EthContractScanner(ethApiKey))

    if args.transaction != None:
        tx = Transaction(args.transaction, fetch, store)
        print(tx.interacted_functions())
        print(tx)