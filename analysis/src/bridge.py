from contract import Contract, Function
from contractstore import ContractStore
from mgowrapper import MongoFetcher
from transaction import Transaction
import json
from enum import Enum
from collections import defaultdict


class Chains(Enum):
    ETH = 1
    POLYGON = 137
    FANTOM = 250
    BSC = 56


class CrossChainTransaction():
    def __init__(self, _from: str, _to: str, token_addr: str, source_chain: str, dest_chain: str) -> None:
        self._from = _from
        self._to = _to
        self.token_addr = token_addr
        self.src_chain = source_chain
        self.dest_chain = dest_chain


class Bridge():
    '''
        Defines a single Bridge object, which represents a cross chain
        bridge. Bridges can be one -> one or one -> many, based on specific
        implementation
    '''

    def __init__(self, db: MongoFetcher,  store: ContractStore, name: str, address: str, source_chain: Chains, inbound_functions, outbound_functions, chains) -> None:
        self.name = name
        self.address = address

        self.store = store
        self.contract = store.get_contract(address)

        self.db = db

        self.inbound_funcs = []
        self.outbound_funcs = []

        self.chains: dict[int, str] = {}

        self.__load_supported_chains(chains)
        self.__load_io_functions(inbound_functions, outbound_functions)

        self.outbound_tx = defaultdict(list)
        self.inbound_tx = defaultdict(list)

        self.source_chain = source_chain

    def __load_supported_chains(self, chains) -> None:
        for c in self.chains:
            self.chains.update(c)

    def __load_io_functions(self, inbound_funcs: [str], outbound_funcs: [str]) -> None:
        """
            Loads in the input / output functions from the JSON file, then finds the 
            corresponding Function item already present in self.contract
        """

        for f in inbound_funcs:
            self.inbound_funcs.append(self.contract.get_function(f))

        for f in outbound_funcs:
            self.outbound_funcs.append(
                (self.contract.get_function(next(iter(f))), list(f.values())[0]))

    def __str__(self) -> str:
        return f"{self.name} at {self.address} \n Inputs: \n {self.inbound_funcs} \n Outputs: \n {self.outbound_funcs}"

    def __repr__(self) -> str:
        return f"{self.name} at {self.address}"

    def load_interactions(self, tx: str, chain_id: int, range: int = 25) -> str:
        """
            Loads all transactions that invoke the output signature within a specified
            range of blocks
        """

    def load_outbound_transactions(self, chain_id: int, start_block: int, end_block: int, amount=100) -> None:
        """
            Loads all transactions that invoke the cross-chain function matching the chainId
            that occur within the range of blocks from start_block + range. Amount controls the
            number of transactions returned.
        """

        txs = self.db.get_block_range(start_block, end_block, self.address)

        for tx_hash in txs:
            tx = Transaction(tx_hash['tx'], self.db, self.store)

            for func, chain_id_location, in self.outbound_funcs:
                if tx.contains_function_value(self.address, func.signature, chain_id_location, chain_id):
                    self.outbound_tx[func.name].append(tx)


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
        with open(filename, 'r') as f:
            data = json.load(f)

            for bridge in data.get("bsc") or []:
                self.bridges.append(Bridge(self.bsc_fetcher, self.bsc_store,
                                           bridge['name'], bridge['address'], Chains.BSC, bridge['inboundFunctions'], bridge['outboundFunctions'], bridge['destChains']))
                self.celer_bridge = self.bridges[0]

            for bridge in data.get("eth") or []:
                self.bridges.append(Bridge(db, self.eth_store,
                                           bridge['name'], bridge['address'], Chains.ETHbridge['inboundFunctions'], bridge['outboundFunctions'], bridge['destChains']))

            for bridge in data.get("polygon") or []:
                self.bridges.append(Bridge(db, self.polygon_store,
                                           bridge['name'], bridge['address'], Chains.POLYGON, bridge['inboundFunctions'], bridge['outboundFunctions'], bridge['destChains']))
