from dataclasses import dataclass
from mgowrapper import MongoFetcher
from errors import MongoTxNotFound
from contract import Contract, Event, Function
from contractstore import ContractStore
import ast

from typing import List, Dict, TUple


@dataclass
class Transfer():
    """
        A single transfer event, corresponding to the transferLogs index in the database
    """

    def __init__(self, _from: str, _to: str, token: str, amount: int, depth: int, _type):
        self._from = _from
        self._to = _to
        self.token = token
        self.amount = amount
        self.depth = depth
        self.type = _type


@dataclass
class TxEvent():
    """
        Represents a logged event from the EVM. 
    """

    def __init__(self, src_contract: Contract, address: str, topics: List[str], data: str):
        self.address = address
        self.topics = topics
        self.signature = topics[0]
        self.contract = src_contract
        self.data = self.__load_data(data)

    def __load_data(self, data: List[str]):
        lengths = self.contract.get_event_arg_lengths(self.topics[0])
        counter = 0
        res = []

        for i in lengths:
            res.append(int(self.data[counter: counter + i]), 16)

            counter += hex(i - 2)  # -2 to offset 0x prefix

        return res


class Call():
    """
        A single call event. Either Call / CallCode / StaticCall / Create / DelegateCall
    """

    def __init__(self, _hash: str, index: int, depth: int, calltype: str, _from: str, _to: str, value: int, gas: int, _input: str, output: str) -> None:
        self.hash = _hash
        self.index = index
        self._from = _from
        self._to = _to
        self.value = value
        self.gas = gas

        self.signature = ""
        self.input: List[int] = self.__load_input(_input)
        self.output = output
        self.type = calltype
        self.depth = depth

        self.event = None

        self.contract = None

    def set_event(self, event: TxEvent):
        self.event = event

    def __load_input(self, _input):
        res = []

        self.signature = _input[2:10]

        [res.append(int(_input[i:i+64].lstrip('0'), 16))
         for i in range(10, len(_input), 64)]
        return res

    def set_contract(self, contract: Contract) -> None:
        self.contract = contract

    def __str__(self) -> str:
        return f"{self.type} | {self.hash}: {self.index}, {self.depth} ({self._from}->{self._to} at contract {self.contract.contract_name}"

    def __repr__(self) -> str:
        return f"{self.type} | {self.hash}: {self.index}, {self.depth} ({self._from}->{self._to} at contract {self.contract.contract_name}"


class Transaction():
    """
        A single transaction object that stores metadata about a transaction, including
        interacted contracts, inputs / outputs, etc
    """

    def __init__(self, hash: str, fetcher: MongoFetcher, store: ContractStore) -> None:
        self.hash: str = hash

        self._to: str = ""
        self._from: str = ""
        self.value: int = 0
        self.gas_price: int = 0
        self.gas_used: int = 0
        self.block: int = 0
        self.store = store

        self.function_signatures: Dict[str, List[str]] = {}

        self.contracts: Dict[str, Contract] = {}
        self.transfers: List[Transfer] = []
        self.events: List[TxEvent] = []
        self.calls: List[Call] = []

        self.is_token_transfer = False

        self.__load_tx(fetcher)

    def __load_tx(self, fetcher: MongoFetcher) -> None:
        """
            Loads a transaction from the mongodb database if present. If not, a MongoTxNotFound
            error is risen. Ensure that the passed collection is correct. 

            Params:
            - fetcher: the MongoFetcher class instance to use to get the tx data
        """

        data = fetcher.get_tx(self.hash)

        if data == None:
            raise MongoTxNotFound(
                f"The transaction was not found in the collection")

        self._to = data['to']
        self._from = data['from']
        self.value = int(data['value'])
        self.gas_price = int(data['gasprice'])
        self.gas_used = int(data['gasused'])
        self.block = int(data['block'])

        self.__load_verified_functions(data['functrace'])
        self.__load_transfer_logs(data['transferlogs'])
        self.__load_signatures()
        self.__load_events(data['eventtrace'].split("\n"))

    def __load_verified_functions(self, functrace: str) -> None:
        """
            Gets all verified contracts that the transaction interacted with in some way, traced
            via the function logs. 
        """

        addresses = set()

        for i in functrace.split("\n"):
            index, calltype, depth, _from, _to, value, gas, _input, output, * \
                _ = i.split(",")

            self.calls.append(Call(self.hash, int(index), int(
                depth), calltype, _from, _to, int(value), int(gas), _input, output))

            addresses.add(_from)
            addresses.add(_to)

        for address in addresses:
            contract = self.store.get_contract(address)

            if contract is not None:
                self.contracts[contract.address] = contract

    def __str__(self) -> str:
        return (f"({self.block}) Transaction {self.hash}: {self._from}->{self._to}\n"
                f"Value: {self.value}, Gas Price: {self.gas_price}, Gas Used: {self.gas_used}\n"
                f"Contracts: \n{self.contracts}")

    def __repr__(self) -> str:
        return f"({self.block}) Transaction {self.hash}: {self._from}->{self._to}\n"

    def __load_signatures(self) -> None:
        """
            Loads all interacted with function signatures:
        """

        for contract in self.contracts.values():
            self.function_signatures.update(contract.get_func_signatures())

    def __load_events(self, logs: List[str]) -> None:
        for event in logs:
            addr, topics_str, data, _type, func, index, = event.split(',')
            topics = ast.literal_eval(topics_str.replace(" ", ","))

            contract = self.contracts.get(addr)

            if contract is not None:
                self.calls[index].set_event(
                    TxEvent(contract, addr, topics, data, _type))

    def __load_transfer_logs(self, logs: List[str]) -> None:
        for transfer in logs.split("\n"):
            _from, _to, token_addr, amount, depth, *_ = transfer.split(",")

            if token_addr in self.contracts:
                _type = self.contracts[token_addr].get_type()
                self.is_token_transfer = True
            else:
                _type = ''
            self.transfers.append(
                Transfer(_from, _to, token_addr, amount, depth, _type))

    def interacted_functions(self) -> List[str]:
        """
            Returns all functions that the transaction interacts with out of
            all the verified contracts the transaction interacts with. Must be
            run after __load_verified_functions
        """

        res = {}

        for call in self.calls:
            if call._to in self.function_signatures and call.input[2:10] in self.function_signatures[call._to]:
                call.set_contract(self.store.get_contract(call._to))

        return [i for i in self.calls if i.contract != None]

    def contains_function(self, address, sig) -> bool:
        """
            Returns whether the current transaction interacts with a specified 
            function signature at the passed address
        """

        if sig != None:
            for call in self.calls:
                if call._to == address and call.signature == sig:
                    return True

        return False

    def contains_function_value(self, address, sig, location, value) -> bool:
        """
            Returns whether the current transaction interacts with a specified 
            function signature at the passed address
        """

        if sig != None:
            for call in self.calls:
                if len(call.input) > location and call._to == address and call.input[0][2:10] == sig and int(call.input[location].lstrip("0"), 16) == value:
                    return True

        return False

    def get_function_value(self, location: int, sig: str = None) -> int:
        '''
            Returns a parameter in the original function call that
            launched the transaction specified by location. Since
            the first arg is the function that is invoked, we add
            one to location (so location = 0 gets the first parameter)
        '''

        if sig is None:
            return self.calls[0].input[location]

        for call in self.calls:
            if call.signature == sig:
                return call.input[location]

        return -1

    def get_event_data_value(self, address: str, event_sig: str, location: int) -> int:
        for event in self.events:
            if event.address == address and event_sig == event.signature:
                return event.data[location]

        return -1

    def get_event_data(self, address: str, event_sig: str) -> List[int]:
        for event in self.events:
            if event.address == address and event_sig == event.signature:
                return event.data

        return []

    def get_token_transfer(self) -> tuple:
        '''
            For now, we just get the first token transfer that is erc20/721
        '''

        for tx in self.transfers or []:
            if tx.type in {'ERC721', 'ERC20'}:
                return (tx._from, tx._to, tx.token, tx.amount)

        return ()

    def emits_illegal_events(self, address: str, sig: str) -> str:
        for event in self.events:
            if event.address != address and event.signature == sig:
                return event.address


class SrcEvents(Enum):
    DSTCHAINID = "dstChainId"
    NONCE = "nonce"
    MAXSLIPPAGE = "maxSlippage"
    RECEIVER = "receiver"
    AMOUNT = "amount"
    TOKEN = "token"


class DestEvents(Enum):
    SENDER = "sender"
    RECEIVER = "receiver"
    TOKEN = "token"
    AMOUNT = "amount"
    SRCCHAINID = "srcChainId"
    SRCTRANSFERID = "srcTransferID"


def CrossChainSend():
    def __init__(self, tx: Transaction, send_func: Function, send_event: Event, bridge_addr: str):
        self.tx = tx
        self.func = send_func
        self.event = send_event
        self.address = bridge_addr

    def get_transfer_by_event(self) -> Tuple[int]:
        data = self.tx.get_event_data(self.address, self.event.signature)
        params = self.event.get_param_names()

        mapping = dict(zip(params, data))

        return
