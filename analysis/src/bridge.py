from contract import Contract, Function
from contractstore import ContractStore
from mgowrapper import MongoFetcher
from transaction import Transaction
import json
from enum import Enum
from collections import defaultdict
import pandas as pd

class Chains(Enum):
    ETH = 1
    POLYGON = 137
    FANTOM = 250
    BSC = 56

    @classmethod
    def resolve_name(cls, name : str) -> int | None:
        if name.lower() == "eth":
            return Chains.ETH
        elif name.lower() == "bsc":
            return Chains.BSC
        elif name.lower() == "polygon" or name.lower() == "poly":
            return Chains.POLYGON
        else:
            return None

class CelerCrossChainTx():
    def __init__(self, _from: str, _to: str, srcChain : Chains, destChain : Chains, tokenAddr : str, tokenAmount : str):

class Endpoint():
    ''' 
        An endpoint is a single bridge instance, correspoding to the bridge type. 
        So a bridge that supports eth, polygon, and bsc will have 3 endpoints, \
        one for each chain
    '''
    def __init__(self, type : Chains, address : str, db : MongoFetcher, store: ContractStore, inbound_functions, outbound_functions, inbound_events, outbound_events) -> None: 
        self.address = address
        self.store = store
        self.contract = store.get_contract(address)
        self.db = db

        self.inbound_funcs = []
        self.outbound_funcs = []
        self.inbound_events = []
        self.outbound_events = []

        self.outbound_tx = pd.DataFrame()
        self.inbound_tx = p

        self.__load(inbound_functions, outbound_functions, inbound_events, outbound_events)

    def __load(self, inbound_funcs: [str, str], outbound_funcs: [str, str], inbound_events: [str, str], outbound_events: [str, str]) -> None:
        """
            Loads in the input / output functions from the JSON file, then finds the 
            corresponding Function item already present in self.contract
        """

        for f in inbound_funcs:
            self.inbound_funcs.append(self.contract.get_function(next(iter(f))))

        for f in outbound_funcs:
            self.outbound_funcs.append(self.contract.get_function(next(iter(f))))

        for e in inbound_events:
            self.inbound_events.append(self.contract.get_event(next(iter(e))))

        for e in outbound_events:
            self.outbound_events.append(self.contract.get_event(next(iter(e))))


    def load_inbounds_transactions(self, start_block: int, end_block : int, amount: int = 100) -> str:
        """
            Loads all transactions that invoke the output signature within a specified
            range of blocks. In this step, the only checked parameters are that the Relay
            function is interacted with. Later, we validate the data of the relay when drawing links
        """

        txs = self.db.get_block_range(start_block, end_block, self.address, amount)

        for tx_hash in txs:
            tx = Transaction(tx_hash['tx'], self.db, self.store)

            for func in self.inbound_funcs:
                if tx.contains_function(self.address, func.signature):
                    self.inbound_funcs.append(tx)


    def load_outbound_transactions(self, start_block: int, end_block: int, amount: int = 100) -> None:
        """
            Loads all transactions that invoke the cross-chain function matching the chainId
            that occur within the range of blocks from start_block + range. Amount controls the
            number of transactions returned.
        """

        txs = self.db.get_block_range(start_block, end_block, self.address, amount)

        for tx_hash in txs:
            tx = Transaction(tx_hash['tx'], self.db, self.store)

            for func in self.outbound_funcs:
                if tx.contains_function(self.address, func.signature):
                    self.outbound_tx.append(tx)

    def get_inbound_transactions(self) -> list:
        return self.inbound_tx
    
    def get_outbound_transactions(self) -> list:
        return self.outbound_tx

class Bridge():
    '''
        Defines a single Bridge object, which represents a cross chain
        bridge. Bridges can be one -> one or one -> many, based on specific
        implementation
    '''

    def __init__(self, name: str, data : [str,str], stores: [str, ContractStore], dbs: [str, MongoFetcher]) -> None:
        self.name = name
        self.stores = stores
        self.dbs = dbs

        self.bridges : [Endpoint] = []

        self.linked_tx : [(Transaction, Transaction)] = []

        self.__load_bridges(data)

    def __load_bridges(self, data : [str,str]) -> None:
        for k,v in data.items():
            chain = Chains.resolve_name(k)

            inbound_funcs = v['inboundFunctions']
            inbound_events = v['inboundEvents']
            outbound_funcs = v['outboundFunctions']
            outbound_events = v['outboundEvents']

            address = v['address']

            endpoint = Endpoint(chain, address, self.dbs[k], self.stores[k], inbound_funcs, outbound_funcs, inbound_events, outbound_events)
            self.bridges.append(endpoint)

    def load_transactions(self, start_block, end_block, amount = 100) -> None:
        for i in self.bridges or []:
            i.load_inbounds_transactions(start_block, end_block, amount)
            i.load_outbound_transactions(start_block, end_block, amount)
    
        
    def __str__(self) -> str:
        return f"{self.name} at {self.address} \n Inputs: \n {self.inbound_funcs} \n Outputs: \n {self.outbound_funcs}"

    def __repr__(self) -> str:
        return f"{self.name} at {self.address}"


class Bridges():
    def __init__(self, eth_store: ContractStore, bsc_store: ContractStore, polygon_store: ContractStore, filename: str, bsc_fetcher: MongoFetcher, eth_fetcher: MongoFetcher, polygon_fetcher: MongoFetcher) -> None:
        self.eth_store = eth_store
        self.eth_fetcher = eth_fetcher

        self.bsc_store = bsc_store
        self.bsc_fetcher = bsc_fetcher

        self.polygon_store = polygon_store
        self.polygon_fetcher = polygon_fetcher

        self.bridges: [Bridge] = []

        self.__load_bridges(filename)

        self.celer_bridge = None

    def __load_bridges(self, filename: str) -> None:
        stores = {"bsc": self.bsc_store, "eth": self.eth_store, "polygon": self.polygon_store}
        dbs = {"bsc": self.bsc_fetcher, "eth": self.eth_fetcher, "polygon": self.polygon_fetcher}

        with open(filename, 'r') as f:
            data = json.load(f)

            for bridge in data.get("Celer") or []:
                self.bridges.append(Bridge("Celer", bridge, stores, dbs))