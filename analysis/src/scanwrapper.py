"""
    Contains definition for etherscan API scanners.

    Currently defined for BSCScan
"""

import requests
from errors import ContractNotFound, InvalidRequest
from contract import Contract
import pprint
import json


class BaseContractScanner():
    """
        Wrapper to read information from a *Scan api and return a Contract object that 
        contains the relevant information about that contract
    """

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def __new__(cls, *args, **kwargs):
        """
            Prevents direct instantiation of the class
        """
        if cls is BaseContractScanner:
            raise TypeError(
                f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls)

    def get_contract(self, address: str) -> Contract:
        """
            Returns a Contract object if present in BSCSCan, or None if there 
            is no verified contract present in BSCScan. In this case, an error is risen also
            to be caught

            Params:
            - address: The address to get the source code for

            Returns:
            - the source code of the address or None if the contract is not veriifed
        """
        try:
            req = requests.get(
                f"{self.base_url}&address={address}&apiKey={self.api_key}")

            if req.status_code != 200:
                raise InvalidRequest(
                    "The passed paremeters were not valid for this endpoint")

            json = req.json()
            if (('status' in json and json['status'] == '0')
                or ('status' in json and json['status'] == '1' and json['result'][0]['SourceCode'] == "")):
                raise ContractNotFound(
                    "The specified contract was not found for this endpoint")

            res = req.json()['result'][0]

            return Contract(address, res['SourceCode'], res['ABI'], res['ContractName'], res['ConstructorArguments'])
        except ContractNotFound:
            return None

    def get_contracts(self, addresses: [str]) -> dict[str, str]:
        """
            Returns a dictionary consisting of the mapping between all provided addresses and a
            Contract object of the address if verified. If the contract does not have a verified source
            code, it is not returned in the dictionary

            Params:
            - addresses: The list of addresses to get source code for

            Returns:
            - a mapping between all addresses that have verified source code and a contract object
        """

        res = {}

        for address in addresses:
            contract = self.get_contract(address)

            if contract != None:
                res[address] = contract

        return res

    def output_contract(self, address: str, filepath=None, output_on_empty=True) -> None:
        """
            Outputs the source code  and abi of a specified address to the file path.
            The code is written to the path in the format {path}/{addresss}.json
            If the file path is not specified, the source code is printed to stdout.

            Params:
            - address: the address to collect the source code for
            - filepath (Optional): the filepath to write the source code to
            - output_on_empty (Optional): whether to still write / output the file if no
              source code is found

            Returns:
            - none
        """

        contract = self.get_contract(address)

        if output_on_empty or code != "":
            if filepath != None:
                if filepath[-1] == "/":
                    filepath = filepath[:-1]

                with open(f"{filepath}/{address}-abi.json", "w") as f:
                    json.dump(contract.abi, f, ensure_ascii=False, indent=4)
                with open(f"{filepath}/{address}-code.json", "w") as f:
                    json.dump(contract.source_code, f,
                              ensure_ascii=False, indent=4)
            else:
                pprint.pprint(contract.abi)


class BSCContractScanner(BaseContractScanner):
    """
        Wrapper for the BSCScan api
    """

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key,
                         "https://api.bscscan.com/api?module=contract&action=getsourcecode&")


class EthContractScanner(BaseContractScanner):
    """
        Wrapper for the EthersScan api
    """

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key,
                         "https://api.etherscan.io/api?module=contract&action=getsourcecode&")
