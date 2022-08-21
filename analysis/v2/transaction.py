import pandas as pd
from mgowrapper import MongoFetcher
from contractstore import ContractStore
from errors import MongoTxNotFound

transfer_sig = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

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

        self.function_signatures: dict[str, [str]] = {}

        self.transfers : pd.DataFrame = None
        self.events : pd.DataFrame = None
        self.calls: pd.DataFrame = None

        self.cross_chain_receiver = None
        self.cross_chain_token = None

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

        self.transfers = pd.DataFrame([x.split(",") for x in data['transferlogs'].split("\n")], 
                            columns=['from', 'to', 'token', 'value', 'depth', 'callnum', 'index', 'type'])
        self.calls = pd.DataFrame([x.split(",") for x in data['functrace'].split("\n")], 
                            columns=['index', 'type', 'depth', 'from', 'to', 'value', 'gas', 'input', 'output', 'callstack', 'calltrace'])
        self.events = pd.DataFrame([x.split(",") for x in data['eventtrace'].split("\n")],
                             columns=['address', 'topics', 'data', 'type', 'func'])

        self.cross_chain_receiver = self.calls.iloc[0]['input'][0:64].lstrip("0")
        self.cross_chain_token = self.calls.iloc[0]['input'][64:128].lstrip("0")

        print(self.cross_chain_receiver)
        print(self.cross_chain_receiver)

    def __load_token_transfers(self) -> None:
        """ 
            Finds all erc20 / erc721 token transfers based on signature and number of topics
        """

        for idx, row in self.events.iterrows():
            if len(row['topics']) == 4 and row['topics'][0] == transfer_sig:
                pass

    def __str__(self) -> str:
        return (f"({self.block}) Transaction {self.hash}: {self._from}->{self._to}\n"
                f"Value: {self.value}, Gas Price: {self.gas_price}, Gas Used: {self.gas_used}\n"
                f"Contracts: \n{self.contracts}")

    def __repr__(self) -> str:
        return f"({self.block}) Transaction {self.hash}: {self._from}->{self._to}\n"


    def interacted_functions(self) -> [str]:
        """
            Returns all functions that the transaction interacts with out of
            all the verified contracts the transaction interacts with. Must be
            run after __load_verified_functions
        """

    def contains_function(self, address : str, sig : str) -> bool:
        """
            Returns whether the current transaction interacts with a specified 
            function signature at the passed address
        """

    def contains_function_value(self, address : str, sig : str, location : str, value : str) -> bool:
        """
            Returns whether the current transaction interacts with a specified 
            function signature at the passed address
        """

    def contains_token_transfer(self, src_addr : str, dest_addr : str, token_addr : str, amount : int) -> bool:
        """
            Returns whether the transactions interacts with a token, transferring a token to a user
        """

        df = self.transfers[self.transfers['from'] == src_addr \
                            & self.transfers['to'] == dest_addr \
                            & self.transfers['token'] == token_addr \
                            & self.transfers['value'] <= amount
                            ]

        return df.size > 0