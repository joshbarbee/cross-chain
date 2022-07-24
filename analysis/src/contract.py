"""
    Defines a contract object that abstracts the various information
    collected from the contract source code.
"""

import json
from Crypto.Hash import keccak


class Event():
    """
        Class to contain information about a specific event
    """

    def __init__(self, name: str, args: []) -> None:
        self.name = name
        self.args = args

        self.k = keccak.new(digest_bits=256)
        self.signature = self.__create_signature()

    def __str__(self) -> str:
        """
            String representation of event
        """

        inputs = [
            f"type: {i['type']} name: {i['name']} indexed: {i['indexed']}" for i in self.args]

        fstring = "\n\t"
        return f"\n{self.name} (0x{self.signature}): \n\t{fstring.join(inputs)}"

    def __repr__(self) -> str:
        """
            Representation of event for lists and such
        """

        inputs = [
            f"type: {i['type']} name: {i['name']} indexed: {i['indexed']}" for i in self.args]

        fstring = "\n\t"
        return f"\n{self.name} (0x{self.signature}): \n\t{fstring.join(inputs)}"

    def __create_signature(self) -> str:
        """
            Creates the function signature of this
        """

        input_types = ",".join([i['type'] for i in self.args])

        string = str.encode(f"{self.name}({input_types})")

        self.k.update(string)

        return self.k.hexdigest()


class Function():
    """
        Class to contain information about a specific function
    """

    def __init__(self, name: str, inputs: list, outputs: list, payable: bool, constant: bool, state_mutability: str) -> None:
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.payable = payable
        self.constant = constant
        self.state_mutability = state_mutability

        self.k = keccak.new(digest_bits=256)
        self.signature = self.__create_signature()

    def __format_io(self) -> str:
        """
            Formats the input and outputs class variables to deal with extraneous values
        """

        inputs = []
        outputs = []

        for i in self.inputs:
            inputs.append({
                type: i['type'],
                name: i['name'],
                internal_type: i['internalType'] if 'internalType' in i else i['type']
            })

        for i in self.outputs:
            outputs.append({
                type: i['type'],
                name: i['name'],
                internal_type: i['internalType'] if 'internalType' in i else i['type']
            })

        self.inputs = inputs
        self.outputs = outputs

    def __str__(self) -> str:
        """
            String representation of a function
        """

        fstring = "\n\t\t"

        inputs_str = fstring.join(
            [f"{i['type']}: {i['name']}" for i in self.inputs]) if len(self.inputs) > 0 else ""
        outputs_str = fstring.join(
            [f"{i['type']}: {i['name']}" for i in self.outputs]) if len(self.outputs) > 0 else ""

        return (f"\n{self.name} (constant: {self.constant}, payable: {self.payable}) state mutability: {self.state_mutability}"
                f"\nSignature: 0x{self.signature}"
                f"\n\tInputs:{fstring}{inputs_str}\n\tOutputs:{fstring}{outputs_str}")

    def __repr__(self) -> str:
        """
            Representation of a function
        """

        fstring = "\n\t\t"

        inputs_str = fstring.join(
            [f"{i['type']}: {i['name']}" for i in self.inputs]) if len(self.inputs) > 0 else ""
        outputs_str = fstring.join(
            [f"{i['type']}: {i['name']}" for i in self.outputs]) if len(self.outputs) > 0 else ""

        return (f"\n{self.name} (constant: {self.constant}, payable: {self.payable}) state mutability: {self.state_mutability}"
                f"\nSignature: 0x{self.signature}"
                f"\n\tInputs:{fstring}{inputs_str}\n\tOutputs:{fstring}{outputs_str}")

    def __create_signature(self) -> str:
        """
            Creates the function signature of this
        """

        input_types = ",".join([i['type'] for i in self.inputs])
        string = str.encode(f"{self.name}({input_types})")

        self.k.update(string)

        return self.k.hexdigest()[0:8]


class Contract():
    """
        Contract class that stores relevant informatation about a particular contract, such as 
        events, source code, abi, name, and address
    """

    def __init__(self, address: str, source_code: str, abi: str, contract_name: str, constructor_args: str) -> None:
        self.address = address
        self.source_code = source_code
        self.abi = json.loads(abi)
        self.contract_name = contract_name
        self.constructor_args = constructor_args

        self.events = self.__load_events()
        self.functions = self.__load_functions()

    def __load_events(self) -> list:
        """
            Loads all events from the abi of the contract into the self.events property
        """

        events = []

        for row in self.abi:
            if row["type"] == "event":
                events.append(Event(row["name"], row["inputs"]))

        return events

    def __load_functions(self) -> list:
        """
            Returns all functions from the abi of the contract
        """

        functions = []

        for row in self.abi:
            if row["type"] == "function":
                payable = row['payable'] if 'payable' in row else False
                constant = row['constant'] if 'constant' in row else False

                functions.append(Function(
                    row["name"], row["inputs"], row["outputs"], payable, constant, row['stateMutability']))

        return functions

    def __str__(self) -> str:
        return (f"Contract: {self.contract_name} at {self.address}\n"
                f"Constructor args: {self.constructor_args}\n"
                f"Events: {[i for i in self.events]}\n"
                f"Functions: {[i for i in self.functions]}")

    def __repr__(self) -> str:
        return (f"Contract: {self.contract_name} at {self.address}\n")

    def __hash__(self) -> int:
        """
            Addresses are already unique, but we hash again to ensure uniform distribution
        """
        return hash(self.address)

    def __eq__(self, o) -> bool:
        """
            Again, taking advantage of address being unique. We avoid any complications with deep nested equalities from the events
            and functions this way
        """ 
        return isinstance(o, type(self)) and o.address == self.address

    def get_func_signatures(self) -> [str]: 
        """ 
            Returns a list of all the function signatures for the contract
        """

        return [i.signature for i in self.functions]