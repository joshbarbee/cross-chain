

class ContractNotFound(Exception):
    """
        Risen when the provided contract is not verified on *Scan
    """


class InvalidRequest(Exception):
    """
        Risen when the apiKey or other parameters passed are an invalid format,
        leading to a non-200 status
    """


class MongoTxNotFound(Exception):
    """
        Risen when the transaction is not found in the provided database and collection
    """


class BlockNotFound(Exception):
    """
        Risen when a provided block number is not found or invalid within Etherscan
    """


class FunctionNotFound(Exception):
    """
        Risen when a input / output function from the JSON file is not found in the 
        contract source code
    """

class EventNotFound(Exception):
    """
        Risen when a contract does not contain the specified event
    """