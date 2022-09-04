from typing import Iterable
from pymongo import MongoClient, CursorType

MONGOURI = "mongodb://127.0.0.1"


class MongoFetcher():
    '''
        Class to interface with mongodb to extract tx info based on 
        block number
    '''

    def __init__(self, db, collection) -> None:
        self.client = MongoClient(MONGOURI)
        self.db = self.client[db]
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

    def get_block_range(self, start: int, end: int, to_address: str = None, limit: int = 1000):
        """
            Gets all transaction hashes by a block range
        """

        query = None

        if to_address != None:
            query = self.collection.find({"block": {"$lte": end, "$gte": start}, "to": to_address}, {
                                         "tx": 1, "_id": 0}, limit=limit)
        else:
            query = self.collection.find({"block": {"$lte": end, "$gte": start}}, {
                                         "tx": 1, "_id": 0}, limit=limit)

        return query
