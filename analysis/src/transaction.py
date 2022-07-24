from mgowrapper import MongoFetcher
from errors import MongoTxNotFound
from contract import Contract, Function
from contractstore import ContractStore

class Call():
    """
        A single call event. Either Call / CallCode / StaticCall / Create / DelegateCall
    """

    def __init__(self, hash : str, index : int, depth : int, calltype : str, _from : str, _to : str, value : int, gas : int, _input : str, output: str) -> None:
        self.hash = hash
        self.index = index
        self._from = _from
        self._to = _to
        self.value = value
        self.gas = gas
        self.input = _input
        self.output = output
        self.type = calltype
        self.depth = depth

        self.contract = None

    def set_contract(self, contract : Contract) -> None:
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

    def __init__(self, hash : str, fetcher : MongoFetcher, store : ContractStore) -> None:
        self.hash : str = hash 

        self._to : str = ""
        self._from : str = ""
        self.value : int = 0
        self.gas_price : int = 0
        self.gas_used : int = 0
        self.block : int = 0
        self.contracts : [Contract] = []
        self.store = store

        self.function_signatures : dict[str, [str]] = {}

        self.calls : [Call] = []

        self.__load_tx(fetcher)
    
    def __load_tx(self, fetcher : MongoFetcher) -> None:
        """
            Loads a transaction from the mongodb database if present. If not, a MongoTxNotFound
            error is risen. Ensure that the passed collection is correct. 

            Params:
            - fetcher: the MongoFetcher class instance to use to get the tx data
        """
        
        data = fetcher.get_tx(self.hash)

        if data == None:
            raise MongoTxNotFound(f"The transaction was not found in the collection")


        self._to = data['to']
        self._from = data['from']
        self.value = int(data['value'])
        self.gas_price = int(data['gasprice'])
        self.gas_used = int(data['gasused'])
        self.block = int(data['block'])

        self.__load_verified_functions(data['functrace'])

    def __load_verified_functions(self, functrace : str) -> None:
        """
            Gets all verified contracts that the transaction interacted with in some way, traced
            via the function logs. 
        """

        addresses = set()

        for i in functrace.split("\n"):
            index, calltype, depth, _from, _to, value, gas, _input, output, *_ = i.split(",")

            self.calls.append(Call(self.hash, int(index), int(depth), calltype, _from, _to, int(value), int(gas), _input, output))

            addresses.add(_from)
            addresses.add(_to)

        for address in addresses:
            contract = self.store.get_contract(address)

            if contract != None:
                self.contracts.append(contract)

    
    def __str__(self) -> str:
        return (f"({self.block}) Transaction {self.hash}: {self._from}->{self._to}\n"
                f"Value: {self.value}, Gas Price: {self.gas_price}, Gas Used: {self.gas_used}\n"
                f"Contracts: \n{self.contracts}")


    def interacted_functions(self) -> [str]:
        """
            Returns all functions that the transaction interacts with out of
            all the verified contracts the transaction interacts with. Must be
            run after __load_verified_functions
        """

        res = {}

        for contract in self.contracts:
            self.function_signatures.update(contract.get_func_signatures())

        for call in self.calls:
            if call._to in self.function_signatures and call.input[2:10] in self.function_signatures[call._to]:
                call.set_contract(self.store.get_contract(call._to))

        return [i for i in self.calls if i.contract != None]