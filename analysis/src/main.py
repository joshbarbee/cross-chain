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
from bridge import Bridges

parser = argparse.ArgumentParser(description=("Contract parser for XScan apis (etherscan, bscscan, etc)"
                                              "\n*If an API key is not provided, then the .env file will "
                                              "be checked. If there is no API key in the .env file, the"
                                              "program will exit\n"
                                              "\nUsage:\n-python contractscanner.py -tx {TX_HASH}"
                                              "\n-python contractscanner.py --chains bsc -tx {TX_HASH}"
                                              "\n-python contractscanner.py  --chains bsc -bk YOUR_BSCSCAN_API_KEY -tx {TX_HASH}"), formatter_class=RawTextHelpFormatter)
parser.add_argument('-tx', '--transaction', type=str,
                    help="the transaction to scan for")
parser.add_argument('-bk', '--bscKey', type=str,
                    help="API Key to use for BSC Scan.")
parser.add_argument('-ek', '--ethKey', type=str,
                    help="API Key to use for Eth Scan")
parser.add_argument('-ep', '--polyKey', type=str,
                    help="API Key to use for Eth Scan")
parser.add_argument('-db', '--database', type=str,
                    help="The database to use for mongodb scanning", required=True)
parser.add_argument('-c', "--chains", nargs='+',
                    help="Chains sto run analysis on \n Supported options:\n-eth\n-bsc\n", required=True)

args = parser.parse_args()

bscStore = None
ethStore = None
polygonStore = None

bscFetcher = MongoFetcher(args.database, "bsc")
ethFetcher = MongoFetcher(args.database, "eth")
polygonFetcher = MongoFetcher(args.database, "poly")

if "bsc" in args.chains:
    bscApiKey = bscApiKey = os.getenv(
        "bscApiKey") if args.bscKey == None else args.bscKey
    bscStore = ContractStore(BSCContractScanner(bscApiKey))

if "eth" in args.chains:
    ethApiKey = ethApiKey = os.getenv(
        "ethApiKey") if args.ethKey == None else args.ethKey
    ethStore = ContractStore(EthContractScanner(ethApiKey))

if "poly" in args.chains:
    polyApiKey = polyApiKey = os.getenv(
        "polyApiKey") if args.polyKey == None else args.polyKey
    polygonStore = ContractStore(PolyContractScanner(polyApiKey))

bridges = Bridges(ethStore, bscStore, polygonStore,
                  "./src/bridges2.json", bscFetcher, ethFetcher, polygonFetcher, args.chains)

bridges.load_transaction(args.transaction)

bridges.link_transaction()

print(bridges.bridges[0].linked_tx)
