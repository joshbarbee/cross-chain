from dataclasses import dataclass
from mgowrapper import MongoFetcher
from errors import MongoTxNotFound
from contract import Contract
from contractstore import ContractStore
import ast

from typing import List, Dict


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

    def __init__(self, src_contract : Contract, address: str, topics: List[str], data: str):
        self.address = address
        self.topics = topics
        self.data = data
        self.contract = src_contract


    def __load_data(self, data):
        # first, get the args of the event that invoked the 


class Call():
    """
        A single call event. Either Call / CallCode / StaticCall / Create / DelegateCall
    """

    def __init__(self, hash: str, index: int, depth: int, calltype: str, _from: str, _to: str, value: int, gas: int, _input: str, output: str) -> None:
        self.hash = hash
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

        self.contract = None

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
        self.__load_events(data['eventtrace'])

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
            addr, topics_str, data, _ = event.split(',')
            topics = ast.literal_eval(topics_str)

            contract = next((x for x in self.contracts if x.address == addr), None)
            self.events.append(TxEvent(contract, addr, topics, data,))

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

    def __load_relay_transfers_logs(self) -> None:
        for event in self.events:

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

    def get_function_value(self, location: int) -> int:
        '''
            Returns a parameter in the original function call that
            launched the transaction specified by location. Since
            the first arg is the function that is invoked, we add
            one to location (so location = 0 gets the first parameter)
        '''

        return self.calls[0].input[location]

    def get_token_transfer(self) -> tuple:
        '''
            For now, we just get the first token transfer that is erc20/721
        '''

        for tx in self.transfers or []:
            if tx.type in {'ERC721', 'ERC20'}:
                return (tx._from, tx._to, tx.token, tx.amount)

        return ()
