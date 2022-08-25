from contract import Contract, Function
from contractstore import ContractStore
from mgowrapper import MongoFetcher
from transaction import Transaction
import json
from enum import IntEnum
from collections import defaultdict
import pandas as pd

from typing import List, Dict

class Chains(IntEnum):
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

    @classmethod
    def to_str(cls, name) -> str:
        if name == Chains.ETH:
            return "eth"
        elif name == Chains.POLYGON:
            return "polygon"
        elif name == Chains.BSC:
            return "bsc"
 
class Endpoint():
    ''' 
        An endpoint is a single bridge instance, correspoding to the bridge type. 
        So a bridge that supports eth, polygon, and bsc will have 3 endpoints, \
        one for each chain
    '''
    def __init__(self, chain : Chains, address : str, db : MongoFetcher, store: ContractStore, inbound_functions, outbound_functions, inbound_events, outbound_events) -> None: 
        self.address = address
        self.store = store
        self.contract = store.get_contract(address)
        self.db = db

        self.chain = chain

        self.inbound_funcs : List[Function] = []
        self.outbound_funcs = []
        self.inbound_events = []
        self.outbound_events = []

        self.outbound_tx = []
        self.inbound_tx = []

        self.invalid_tx = []

        self.__load(inbound_functions, outbound_functions, inbound_events, outbound_events)
    
    def __hash__(self) -> int:
        return hash(self.address)

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o):
            if __o == self:
                return True
        
        return False

    def __load(self, inbound_funcs: Dict [str, str], outbound_funcs: Dict [str, str], inbound_events: Dict [str, str], outbound_events: Dict [str, str]) -> None:
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


    def load_inbound_transactions(self, start_block: int, end_block : int, amount: int = 100) -> str:
        """
            Loads all transactions that invoke the output signature within a specified
            range of blocks. In this step, the only checked parameters are that the Relay
            function is interacted with. Later, we validate the data of the relay when drawing links
        """

        txs = self.db.get_block_range(start_block, end_block, self.address, amount)

        for tx_hash in txs:
            tx = Transaction(tx_hash['tx'], self.db, self.store)
            for func in self.inbound_funcs:
                if tx.contains_function(self.address, func.signature) and tx.is_token_transfer:
                    self.inbound_tx.append(tx)


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
                if tx.contains_function(self.address, func.signature) and tx.is_token_transfer:
                    self.outbound_tx.append(tx)

    def get_inbound_transactions(self) -> list:
        return self.inbound_tx
    
    def get_outbound_transactions(self) -> list:
        return self.outbound_tx

    def get_src_token_transfers(self) -> pd.DataFrame:
        temp = {}

        for tx in self.inbound_tx:
            data = tx.get_token_transfer()

            if len(data) < 4:
                continue

            _from, _to, token_addr, amount = data

            temp[tx.hash] = [tx.hash, _from, _to, token_addr, int(self.chain), int(amount,16)]

        return pd.DataFrame.from_dict(temp, orient='index', columns=['srcHash', 'srcSender','srcReceiver','srcTokenAddr','chainId', 'srcValue'])

    def get_dest_token_transfers(self) -> pd.DataFrame:
        temp = {}

        for tx in self.outbound_tx:
            data = tx.get_token_transfer()

            if len(data) < 4:
                continue

            _from, _to, token_addr, amount = data

            chain_id = tx.get_function_value(3)

            src_receiver = hex(tx.get_function_value(0))

            temp[tx.hash] = [tx.hash, _from, _to, token_addr, chain_id, int(amount,16), src_receiver]
            
        return pd.DataFrame.from_dict(temp, orient='index', columns=['destHash', 'destSender','destReceiver','destTokenAddr','chainId', 'destValue', 'srcReceiver'])


    def verify_src_token_transfer(self):
        temp = []

        for tx in self.outbound_tx:
            if tx.contains_token_transfer(tx._from, self.address, tx.cross_chain_token):
                temp.append(tx)
            else:
                self.invalid_tx.append(tx)
        
        self.outbound_tx = temp
    
    def verify_dest_token_transfer(self):
        temp = []

        for tx in self.inbound_tx:
            if tx.contains_token_transfer(tx.cross_chain_receiver, self.address, tx.cross_chain_token):
                temp.append(tx)
            else:
                self.invalid_tx.append(tx)
        
        self.inbound_tx = temp


class Bridge():
    '''
        Defines a single Bridge object, which represents a cross chain
        bridge. Bridges can be one -> one or one -> many, based on specific
        implementation
    '''

    def __init__(self, name: str, data : Dict [str,str], stores: Dict [str, ContractStore], dbs: Dict [str, MongoFetcher]) -> None:
        self.name = name
        self.stores = stores
        self.dbs = dbs

        self.bridges : Dict [str, Endpoint] = self.__load_bridges(data)

        self.linked_tx : pd.DataFrame = pd.DataFrame(columns=[
                        'srcHash', 'srcSender','srcReceiver','srcTokenAddr','srcChainId', 'srcValue', 'destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'destChainId', 'destValue'])

        self.invalid_tx : pd.DataFrame = pd.DataFrame(columns=['tx', 'srcChainId', 'reason'])

    def __load_bridges(self, data : Dict [str,str]) -> None:
        res = {}

        for c in data:
            v = data[c]
            chain = Chains.resolve_name(c)

            inbound_funcs = v['inboundFunctions']
            inbound_events = v['inboundEvents']
            outbound_funcs = v['outboundFunctions']
            outbound_events = v['outboundEvents']

            address = v['address']

            endpoint = Endpoint(chain, address, self.dbs[c], self.stores[c], inbound_funcs, outbound_funcs, inbound_events, outbound_events)
            
            res[chain] = endpoint

        return res

    def load_transactions(self, start_block, end_block, amount = 100) -> None:
        self.bridges[Chains.ETH].load_outbound_transactions(start_block, end_block, amount)
        relative_block = self.get_relative_chain_block(start_block, Chains.ETH, Chains.BSC)

        self.bridges[Chains.BSC].load_inbound_transactions(relative_block, relative_block + 100, amount)

    def link_transactions(self) -> None:
        self.link_token_transfers()

        self.find_invalid_transfer_amt()

    def link_token_transfers(self) -> None:
        dest_txs = pd.DataFrame(columns=['destSender','destReceiver','destTokenAddr','chainId', 'destValue', 'srcReceiver'])
        src_txs = pd.DataFrame(columns=['srcSender','srcReceiver','srcTokenAddr','chainId', 'srcValue'])

        for i in self.bridges.values():
            src_txs = pd.concat([src_txs, i.get_src_token_transfers()], ignore_index=True)

            dest_txs = pd.concat([dest_txs, i.get_dest_token_transfers()], ignore_index=True)

        self.linked_tx = dest_txs.merge(src_txs, on=['srcReceiver','chainId'], how='outer')

    def find_invalid_transfer_amt(self) -> None:
        self.linked_tx = self.linked_tx[self.linked_tx['destValue'] <= self.linked_tx['srcValue']]
        
    def get_relative_chain_block(self, block : int, src_chain: Chains, dest_chain : Chains) -> int: 
        if src_chain not in self.bridges or dest_chain not in self.bridges:
            raise ValueError

        timestamp = self.stores[Chains.to_str(src_chain)].get_block_timestamp(block)

        return self.stores[Chains.to_str(dest_chain)].get_closest_block(timestamp)
            
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

        self.bridges: List [Bridge] = []

        self.__load_bridges(filename)

        self.celer_bridge = None

    def __load_bridges(self, filename: str) -> None:
        stores = {"bsc": self.bsc_store, "eth": self.eth_store, "polygon": self.polygon_store}
        dbs = {"bsc": self.bsc_fetcher, "eth": self.eth_fetcher, "polygon": self.polygon_fetcher}

        with open(filename, 'r') as f:
            data = json.load(f)

            for bridge in data:
                self.bridges.append(Bridge(bridge, data[bridge], stores, dbs))