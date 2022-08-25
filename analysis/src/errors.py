

class ContractNotFound(BaseException):
    """
        Risen when the provided contract is not verified on *Scan
    """


class InvalidRequest(BaseException):
    """
        Risen when the apiKey or other parameters passed are an invalid format,
        leading to a non-200 status
    """


class MongoTxNotFound(BaseException):
    """
        Risen when the transaction is not found in the provided database and collection
    """


class BlockNotFound(BaseException):
    """
        Risen when a provided block number is not found or invalid within Etherscan
    """


class FunctionNotFound(BaseException):
    """
        Risen when a input / output function from the JSON file is not found in the 
        contract source code
    """

class EventNotFound(BaseException):
    """
        Risen when a contract does not contain the specified event
    """