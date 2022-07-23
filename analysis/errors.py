

class ContractNotFound(Exception):
    """
        Risen when the provided contract is not verified on *Scan
    """


class InvalidRequest(Exception):
    """
        Risen when the apiKey or other parameters passed are an invalid format,
        leading to a non-200 status
    """
