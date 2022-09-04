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
    def resolve_name(cls, name: str) -> int | None:
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

    def __init__(self, chain: Chains, address: str, db: MongoFetcher, store: ContractStore, dest_functions, src_functions, dest_events, src_events) -> None:
        self.address = address
        self.store = store
        self.contract = self.store.get_contract(address)
        self.db = db

        self.chain = chain

        self.dest_funcs: List[Function] = []
        self.src_funcs: List[Function] = []

        self.src_tx: Transaction = None
        self.dest_tx: List[Transaction] = []

        self.invalid_tx: List[Transaction] = []

        self.__load(dest_functions, src_functions,
                    dest_events, src_events)

    def __hash__(self) -> int:
        return hash(self.address)

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o):
            if __o == self:
                return True

        return False

    def __load(self, dest_funcs: Dict[str, str], src_funcs: Dict[str, str], dest_events: Dict[str, str], src_events: Dict[str, str]) -> None:
        """
            Loads in the input / output functions from the JSON file, then finds the 
            corresponding Function item already present in self.contract
        """

        for f in dest_funcs:
            self.dest_funcs.append(
                self.contract.get_function(next(iter(f))))

        for f in src_funcs:
            self.src_funcs.append(
                self.contract.get_function(next(iter(f))))

    def load_src_transaction(self, tx: str) -> None:
        """
            Loads in a singular src transaction from a tx hash.
        """

        tx_query = self.db.get_tx(tx)

        tx = Transaction(tx_query['tx'], self.db, self.store)

        for func in self.src_funcs:
            if tx.contains_function(self.address, func.signature) and tx.is_token_transfer:
                self.src_tx = tx

    def get_src_transaction_chain(self) -> Chains:
        if self.src_tx is None:
            return 0

        chain_id = self.src_tx.get_function_value(3)

        return Chains(chain_id)

    def load_dest_transactions(self, start_block: int, end_block: int, amount: int = 100) -> None:
        """
            Loads all transactions that invoke the output signature within a specified
            range of blocks. In this step, the only checked parameters are that the Relay
            function is interacted with. Later, we validate the data of the relay when drawing links
        """

        txs = self.db.get_block_range(
            start_block, end_block, self.address, amount)

        for tx_hash in txs:
            tx = Transaction(tx_hash['tx'], self.db, self.store)
            for func in self.dest_funcs:
                if tx.contains_function(self.address, func.signature) and tx.is_token_transfer:
                    self.dest_tx.append(tx)

    def get_dest_transactions(self) -> List[Transaction]:
        return self.dest_tx

    def get_src_transactions(self) -> Transaction:
        return self.src_tx

    def get_dest_token_transfers(self) -> pd.DataFrame:
        temp = {}

        for tx in self.dest_tx:
            data = tx.get_token_transfer()

            if len(data) < 4:
                continue

            _from, _to, token_addr, amount = data

            temp[tx.hash] = [tx.hash, _from, _to,
                             token_addr, int(self.chain), int(amount, 16)]

        return pd.DataFrame.from_dict(temp, orient='index', columns=['destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'chainId', 'destValue'])

    def get_src_token_transfers(self) -> pd.DataFrame:
        temp = {}

        if self.src_tx is None:
            return pd.DataFrame(columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'chainId', 'srcValue', 'destReceiver'])

        data = self.src_tx.get_token_transfer()

        if len(data) < 4:
            return pd.DataFrame(columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'chainId', 'srcValue', 'destReceiver'])

        _from, _to, token_addr, amount = data

        chain_id = self.src_tx.get_function_value(3)

        src_receiver = hex(self.src_tx.get_function_value(0))

        temp[self.src_tx.hash] = [self.src_tx.hash, _from,
                                       _to, token_addr, chain_id, int(amount, 16), src_receiver]

        return pd.DataFrame.from_dict(temp, orient='index', columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'chainId', 'srcValue', 'destReceiver'])

    def verify_dest_token_transfer(self):
        temp = []

        for tx in self.dest_tx:
            if tx.contains_token_transfer(tx.cross_chain_receiver, self.address, tx.cross_chain_token):
                temp.append(tx)
            else:
                self.invalid_tx.append(tx)

        self.dest_tx = temp


class Bridge():
    '''
        Defines a single Bridge object, which represents a cross chain
        bridge. Bridges can be one -> one or one -> many, based on specific
        implementation
    '''

    def __init__(self, name: str, data: Dict[str, str], stores: Dict[str, ContractStore], dbs: Dict[str, MongoFetcher], chains : List[str]) -> None:
        self.name = name
        self.stores = stores
        self.dbs = dbs

        self.bridges: Dict[str, Endpoint] = self.__load_bridges(data, chains)

        self.current_transaction = None

        self.linked_tx: pd.DataFrame = pd.DataFrame(columns=[
            'srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'destChainId', 'destValue'])

        self.invalid_tx: pd.DataFrame = pd.DataFrame(
            columns=['tx', 'srcChainId', 'reason'])

    def __load_bridges(self, data: Dict[str, str], chains : List[Chains]) -> None:
        res = {}

        for c in data:
            v = data[c]
            chain = Chains.resolve_name(c)

            dest_funcs = v['inboundFunctions']
            dest_events = v['inboundEvents']
            src_funcs = v['outboundFunctions']
            src_events = v['outboundEvents']

            address = v['address']

            if chain in chains:
                endpoint = Endpoint(chain, address, self.dbs[c], self.stores[c],
                                    dest_funcs, src_funcs, dest_events, src_events)

                res[chain] = endpoint

        return res

    def load_transaction(self, src_chain: Chains, tx: str, _range=100, amount=100):
        """
            Loads in a transaction on a particular bridge if the chain of that bridge is the
            same as the passed chain
        """

        self.bridges[src_chain].load_src_transaction(tx)

        dest_chain = self.bridges[src_chain].get_src_transaction_chain()
        relative_block = self.get_relative_chain_block(
            self.bridges[src_chain].src_tx.block, src_chain, dest_chain)

        self.bridges[dest_chain].load_dest_transactions(
            relative_block, relative_block + _range, amount)

    def link_transactions(self) -> None:
        self.link_token_transfers()

        self.find_invalid_transfer_amt()

    def link_token_transfers(self) -> None:
        dest_txs = pd.DataFrame(columns=[
                                'destSender', 'destReceiver', 'destTokenAddr', 'chainId', 'destValue'])
        src_txs = pd.DataFrame(
            columns=['srcSender', 'srcReceiver', 'srcTokenAddr', 'chainId', 'srcValue', 'destReceiver'])

        for i in self.bridges.values():
            src_txs = pd.concat(
                [src_txs, i.get_src_token_transfers()], ignore_index=True)

            dest_txs = pd.concat(
                [dest_txs, i.get_dest_token_transfers()], ignore_index=True)

        self.linked_tx = src_txs.merge(
            dest_txs, on=['destReceiver', 'chainId'], how='outer')

    def find_invalid_transfer_amt(self) -> None:
        self.linked_tx = self.linked_tx[self.linked_tx['destValue']
                                        <= self.linked_tx['srcValue']]

    def get_relative_chain_block(self, block: int, src_chain: Chains, dest_chain: Chains) -> int:
        if src_chain not in self.bridges or dest_chain not in self.bridges:
            raise ValueError

        timestamp = self.stores[Chains.to_str(
            src_chain)].get_block_timestamp(block)

        return self.stores[Chains.to_str(dest_chain)].get_closest_block(timestamp)

    def __str__(self) -> str:
        return f"{self.name} at {self.address} \n Inputs: \n {self.dest_funcs} \n Outputs: \n {self.src_funcs}"

    def __repr__(self) -> str:
        return f"{self.name} at {self.address}"


class Bridges():
    def __init__(self, eth_store: ContractStore, bsc_store: ContractStore, polygon_store: ContractStore, filename: str, bsc_fetcher: MongoFetcher, eth_fetcher: MongoFetcher, polygon_fetcher: MongoFetcher, chains : List[str]) -> None:
        self.eth_store = eth_store
        self.eth_fetcher = eth_fetcher

        self.bsc_store = bsc_store
        self.bsc_fetcher = bsc_fetcher

        self.polygon_store = polygon_store
        self.polygon_fetcher = polygon_fetcher

        self.bridges: List[Bridge] = []

        self.__load_bridges(filename, chains)

        self.celer_bridge = None

    def __load_bridges(self, filename: str, chains : List[str]) -> None:
        stores = {"bsc": self.bsc_store, "eth": self.eth_store,
                  "poly": self.polygon_store}
        dbs = {"bsc": self.bsc_fetcher, "eth": self.eth_fetcher,
               "poly": self.polygon_fetcher}

        formatted_chains = [Chains.resolve_name(chain) for chain in chains]

        with open(filename, 'r') as f:
            data = json.load(f)

            for bridge in data:
                self.bridges.append(Bridge(bridge, data[bridge], stores, dbs, formatted_chains))

    def load_transaction(self, tx: str) -> None:
        for bridge in self.bridges:
            if self.eth_store.get_tx_exists(tx):
                bridge.load_transaction(Chains.ETH, tx)
            elif self.bsc_store.get_tx_exists(tx):
                bridge.load_transaction(Chains.BSC, tx)
            elif self.polygon_store.get_tx_exists(tx):
                bridge.load_transaction(Chains.POLYGON, tx)

    def link_transaction(self) -> None:
        for bridge in self.bridges:
            bridge.link_transactions()

