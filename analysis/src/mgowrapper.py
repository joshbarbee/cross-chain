from typing import Iterable
from pymongo import MongoClient, CursorType

MONGOURI = "mongodb://127.0.0.1"


class MongoFetcher():
    '''
        Class to interface with mongodb to extract tx info based on 
        block number
    '''

    def __init__(self, collection) -> None:
        self.client = MongoClient(MONGOURI)
        self.db = self.client.ethereum
        self.collection = self.db[collection]
        self.block: int = 1

    def get_block(self, n: int = None) -> None:
        '''
            Gets all transactions in the mongodb at a certain index 
            N is an optional argument that ifnot specified, we will read
            in the next block 
        '''
        if n == None:
            n = self.block

        txs = self.collection.find({"block": str(n)})

        self.block = n + 1

        return txs

    def get_tx(self, tx: str = "") -> Iterable[CursorType]:
        '''
            Gets a single transaction based on the tx argument, which is the 
            hash of the transaction
        '''
        if tx == "":
            return list(self.collection.aggregate([{"$sample": {"size": 1}}]))[0]
        return self.collection.find_one({"tx": tx})
