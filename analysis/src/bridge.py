from contract import Contract, Function, Event
from contractstore import ContractStore
from mgowrapper import MongoFetcher
from transaction import Transaction, CrossChainSend
import json
from enum import IntEnum, Enum
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

        self.src_events: List[Event] = []
        self.dest_events: List[Event] = []

        self.src_tx: CrossChainSend = None
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
            corresponding Function / Event object already present in self.contract, adding
            to the self.src/dest_func/event object

            @param dest_funcs: a dict consisting of the outboundFunctions section of the bridge inputfile
            @param src_funcs: a dict consisting of the inboundFunctions section of the bridge input file
            @param dest_events: a dict consisting of the outboundEvents section of the bridge input file
            @param src_events: a dict consisting of the src_events section of the bridge input file
        """

        for f in dest_funcs:
            self.dest_funcs.append(
                self.contract.get_function(next(iter(f))))

        for f in src_funcs:
            self.src_funcs.append(
                self.contract.get_function(next(iter(f))))

        for e in dest_events:
            self.dest_events.append(self.contract.get_event(next(iter(e))))

        for e in src_events:
            self.src_events.append(self.contract.get_event(next(iter(e))))

    def load_src_transaction(self, tx: str) -> None:
        """
            Loads in a singular src transaction from a tx hash. If the transaction interacts
            with an outbound function (send/sendNative), self.src_tx is set to the Transaction 
            object, else it remains None

            @param tx: the tx hash to load on the source chain
        """

        tx_query = self.db.get_tx(tx)

        tx = Transaction(tx_query['tx'], self.db, self.store)

        for func in self.src_funcs:
            if tx.contains_function(self.address, func.signature) and tx.is_token_transfer:
                self.src_tx = tx

    def get_src_transaction_chain(self) -> Chains:
        """
            Determines
        """
        if self.src_tx is None:
            return 0

        chain_id = self.src_tx.get_function_value(3)

        return Chains(chain_id)

    def load_dest_transactions(self, start_block: int, end_block: int, amount: int = 100) -> None:
        """
            Loads all transactions that invoke the output signature within a specified
            range of blocks. In this step, the only checked parameters are that the Relay / dest_funcs
            function is interacted with. Later, we validate the data of the relay when drawing links

            @param start_block : the block to start searching at
            @param end_block : the block to end searching at
            @param amount : the number of individual transactions to scan (default 100)
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

    def get_dest_event_token_transfers(self) -> pd.DataFrame:
        ''' 
            Determine token transfers on the destination chain from emitted events.

            Does check that the address is the address of the smart contract, but 
            does not have any index check, since not all events trace indices

            @returns a dataframe consisting of the collected information:
                | destHash | destSender | destReceiver | destTokenAddr | destChainId | destValue

            TODO - better logic for linking transfers by events
        '''

        temp = {}

        for tx in self.dest_tx:
            for event in self.dest_events:
                data = tx.get_event_data(self.address, event_sig)
                if len(data) < 4:
                    continue

                _, _from, _to, token_addr, amount, *_ = data

                temp[tx.hash] = [tx.hash, _from, _to,
                                 token_addr, int(self.chain), int(amount, 16)]

        return pd.DataFrame.from_dict(temp, orient='index', columns=['destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'destChainId', 'destValue'])

    def get_dest_token_transfers(self) -> pd.DataFrame:
        '''
            Determines token transfers on the destination chain from the token_transfer() function of
            the transaction. This methos is *safer*, since transfer logs rely less on events. 

            @returns a dataframe consisting of the collected information:
                | destHash | destSender | destReceiver | destTokenAddr | destChainId | destValue

        '''
        temp = {}

        for tx in self.dest_tx:
            data = tx.get_token_transfer()

            if len(data) < 4:
                continue

            _from, _to, token_addr, amount = data

            temp[tx.hash] = [tx.hash, _from, _to,
                             token_addr, int(self.chain), int(amount, 16)]

        return pd.DataFrame.from_dict(temp, orient='index', columns=['destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'destChainId', 'destValue'])

    def get_src_token_transfers(self) -> pd.DataFrame:
        '''
            Determines token transfer information from the src_tx object. We collect information from the 
            initial transaction function call to get the destination chain id and destination receiver.

            @returns a pandas dataframe consisting of the following columns
                | srcHash | srcSender | srcReceiver | srcTokenAddr | srcChainId | srcValue | destChainId | destReceiver
        '''
        temp = {}

        if self.src_tx is None:
            return pd.DataFrame(columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destChainId', 'destReceiver'])

        data = self.src_tx.get_token_transfer()

        if len(data) < 4:
            return pd.DataFrame(columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destChainId', 'destReceiver'])

        _from, _to, token_addr, amount = data

        dest_chain_id = self.src_tx.get_function_value(3)

        dest_receiver = hex(self.src_tx.get_function_value(0))

        temp[self.src_tx.hash] = [self.src_tx.hash, _from,
                                  _to, token_addr, int(self.chain), int(amount, 16), dest_chain_id, dest_receiver]

        return pd.DataFrame.from_dict(temp, orient='index', columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destChainId', 'destReceiver'])


class Bridge():
    '''
        Defines a single Bridge object, which represents a cross chain
        bridge. Bridges can be one -> one or one -> many, based on specific
        implementation
    '''

    def __init__(self, name: str, data: Dict[str, str], stores: Dict[str, ContractStore], dbs: Dict[str, MongoFetcher], chains: List[str]) -> None:
        self.name = name
        self.stores = stores
        self.dbs = dbs

        self.bridges: Dict[str, Endpoint] = self.__load_endpoints(data, chains)

        self.current_transaction = None

        self.linked_tx: pd.DataFrame = pd.DataFrame(columns=[
            'srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'destChainId', 'destValue'])

        self.invalid_tx: pd.DataFrame = pd.DataFrame(
            columns=['type'', hash', 'sender', 'receiver', 'tokenAddr', 'chainId', 'value', 'reason'])

    def __load_endpoints(self, data: Dict[str, str], chains: List[Chains]) -> None:
        ''' 
            Loads the various bridge instances from the JSON bridge input data, creating
            an Endpoint object for each.

            @param data : the json input data of the bridge information
            @param chains : a list consisting of the supported chains for the specific bridge, aliased to the Chains enum

            *Note a bridge instance is a single instance of a bridge on a single chain (an endpoint). A 
            bridge object holds information about multiple endpoints, to aggregate data across chains
        '''
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
            Loads in a transaction on the source chain, then determines the relative 
            range of transactions on the destination chain, and loads all possible
            transactions over that range.

            @param src_chain : the chain to search for the initial transaction on
            @param tx : the transaction hash to look for on the original chain
            @param _range : the number of blocks we should permit the destination transaction
            to occur maximum after (default 100)
            @param amount : the max amount of transactions to search for on the destination
            chain (default 100)
        """

        self.bridges[src_chain].load_src_transaction(tx)

        dest_chain = self.bridges[src_chain].get_src_transaction_chain()
        relative_block = self.get_relative_chain_block(
            self.bridges[src_chain].src_tx.block, src_chain, dest_chain)

        self.bridges[dest_chain].load_dest_transactions(
            relative_block, relative_block + _range, amount)

    def link_transactions(self) -> None:
        '''
            Links transactions across multiple chains via invoking various
            helper functions 
        '''
        self.link_token_transfers()

        self.find_invalid_transfer_amt()

    def link_token_transfers(self) -> None:
        '''
            Collects all source and destination token transfer information 
            from each endpoint, joining the two dataframes on the destChainId
            column and the destReceiver column. If those two columns do not match,
            it is impossible to draw any link 

            TODO: is it safe to not draw any link if receiver is different? What 
            if that is a vulnerability?
        '''
        dest_txs = pd.DataFrame(columns=[
                                'destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'destChainId', 'destValue'])
        src_txs = pd.DataFrame(
            columns=['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destChainId', 'destReceiver'])

        for i in self.bridges.values():
            src_txs = pd.concat(
                [src_txs, i.get_src_token_transfers()], ignore_index=True)

            dest_txs = pd.concat(
                [dest_txs, i.get_dest_token_transfers()], ignore_index=True)

        self.linked_tx = src_txs.merge(
            dest_txs, on=['destReceiver', 'destChainId'], how='outer')

    def find_invalid_transfer_amt(self) -> None:
        '''
            Reduces self.linked_tx to the set of linked transactions where the received
            token amount on the destination chain is less than or equal to on the source
            chain. Any transactions that have a destination chain transfer amount greater
            than the source chain is added to the invalid_tx dataframe 
        '''
        self.linked_tx = self.linked_tx[self.linked_tx['destValue']
                                        <= self.linked_tx['srcValue']]

        self.invalid_tx = self.linked_tx[self.linked_tx['destValue']
                                         > self.linked_tx['srcValue']]

    def get_relative_chain_block(self, block: int, src_chain: Chains, dest_chain: Chains) -> int:
        '''
            Determines the block number that was most closely minted on a different chain
            relative to a block number on the source chain.

            @param block : the block number on the source chain
            @param src_chain : the chain that the block number originated from
            @param dest_chain : the chain to get the relative block number for 

            @returns an int consisting of the closest block that was created on dest_chain
            relative to block on the src_chain 
        '''
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
    def __init__(self, eth_store: ContractStore, bsc_store: ContractStore, polygon_store: ContractStore, filename: str, bsc_fetcher: MongoFetcher, eth_fetcher: MongoFetcher, polygon_fetcher: MongoFetcher, chains: List[str]) -> None:
        self.eth_store = eth_store
        self.eth_fetcher = eth_fetcher

        self.bsc_store = bsc_store
        self.bsc_fetcher = bsc_fetcher

        self.polygon_store = polygon_store
        self.polygon_fetcher = polygon_fetcher

        self.bridges: List[Bridge] = []

        self.__load_bridges(filename, chains)

        self.celer_bridge = None

    def __load_bridges(self, filename: str, chains: List[str]) -> None:
        ''' 
            Loads in the bridge information from the JSON file, creating
            a Bridge object for each individual bridge instance

            @param filename : the file to open to read
            @param chains : a list consisting of a string of each supported chain (via cmd-line args)
        '''
        stores = {"bsc": self.bsc_store, "eth": self.eth_store,
                  "poly": self.polygon_store}
        dbs = {"bsc": self.bsc_fetcher, "eth": self.eth_fetcher,
               "poly": self.polygon_fetcher}

        formatted_chains = [Chains.resolve_name(chain) for chain in chains]

        with open(filename, 'r') as f:
            data = json.load(f)

            for bridge in data:
                self.bridges.append(
                    Bridge(bridge, data[bridge], stores, dbs, formatted_chains))

    def load_transaction(self, tx: str) -> None:
        ''' 
            Loads in a transaction on a bridge based on the transaction hash. 
            Within bridge.load_transaction, both the source transaction and the potential
            corresponding destination transactions are loaded, but not linked yet.

            @param tx : the transaction has to search for on the source chain
        '''

        for bridge in self.bridges:
            if self.eth_store.get_tx_exists(tx):
                bridge.load_transaction(Chains.ETH, tx)
            elif self.bsc_store.get_tx_exists(tx):
                bridge.load_transaction(Chains.BSC, tx)
            elif self.polygon_store.get_tx_exists(tx):
                bridge.load_transaction(Chains.POLYGON, tx)

    def link_transaction(self) -> None:
        '''
            Links the source and destination transactions from the previous information
            loaded via load_transaction. Main entrypoint for analysis 
        '''
        for bridge in self.bridges:
            bridge.link_transactions()

    def output_transaction(self, filename: str = "") -> None:
        '''
            Outputs the current state of all bridges .linked_tx 
            variables as a pandas dataframe. If filename is defined, 
            then the output is written to the filename, else stdout

            @param filename : the file name (and path) to write the output to as a csv
        '''

        res = pd.DataFrame(columns=[
            'srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'srcChainId', 'srcValue', 'destChainId', 'destReceiver', 'destHash', 'destSender',  'destTokenAddr', 'destValue'])

        linked_tx = [i.linked_tx for i in self.bridges]

        res = pd.concat([res, *linked_tx], ignore_index=True, axis=0)

        if filename != "":
            res.to_csv(path_or_buf=filename)
        else:
            print(res.head())
