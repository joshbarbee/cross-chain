from contract import Contract
from scanwrapper import EthContractScanner, BSCContractScanner, BaseContractScanner

class ContractStore():
    """
        Class to manage the storing of contracts in computer memory. Used so that transactions do not recreate the same contract
        multiple times

        Params:
        - scanner (The API scanner to use (BSCCOntractScanner, EthContractScanner, etc))
    """

    def __init__(self, scanner : BSCContractScanner | EthContractScanner):
        self.contracts : dict[string, Contract] = {}   
        self.scanner = scanner

    def get_contract(self, address) -> Contract:
        """
            Checks to see if the contract first exists locally, then checks the *Scan APIs to see if the contract can be loaded.
            If the contract is not loaded, none is returned

            Params:
            - address: the address of the contract to load
        """

        contract : Contract = None

        if address in self.contracts:
            contract = self.contracts[address]
        else: 
            contract = self.scanner.get_contract(address)
            
            self.contracts[address] = contract

        return contract
