from contract import Contract
from scanwrapper import EthContractScanner, BSCContractScanner, PolyContractScanner


class ContractStore():
    """
        Class to manage the storing of contracts in computer memory. Used so that transactions do not recreate the same contract
        multiple times

        Params:
        - scanner (The API scanner to use (BSCCOntractScanner, EthContractScanner, etc))
    """

    def __init__(self, scanner: BSCContractScanner | EthContractScanner | PolyContractScanner):
        self.contracts: dict[str, Contract] = {}
        self.scanner = scanner

    def get_contract(self, address: str) -> Contract:
        """
            Checks to see if the contract first exists locally, then checks the *Scan APIs to see if the contract can be loaded.
            If the contract is not loaded, none is returned

            Params:
            - address: the address of the contract to load
        """

        contract: Contract = None

        if address in self.contracts:
            contract = self.contracts[address]
        else:
            contract = self.scanner.get_contract(address)

            self.contracts[address] = contract

        return contract

    def get_block_timestamp(self, block: int) -> int:
        '''
            Returns a timestamp of when a block was created, in Unix time 
        '''
        return self.scanner.get_block_timestamp(block)

    def get_closest_block(self, timestamp: int) -> int:
        '''
            Returns the block that was created the closest to the passed timestamp 
        '''
        return self.scanner.get_closest_block(timestamp)

    def get_tx_exists(self, tx: str) -> bool:
        '''
            Returns whether a Transaction exists within the specific ContractStore and Scanner 
        '''
        return self.scanner.get_tx_exists(tx)
