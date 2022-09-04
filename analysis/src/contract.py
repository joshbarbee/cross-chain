"""
    Defines a contract object that abstracts the various information
    collected from the contract source code.
"""

import json
from Crypto.Hash import keccak
from errors import FunctionNotFound, EventNotFound
import ethtypes

erc20_sigs = [
    "dd62ed3e90e97b3d417db9c0c7522647811bafca5afc6694f143588d255fdfb4"
    "095ea7b334ae44009aa867bfb386f5c3b4b443ac6f0ee573fa91c4608fbadfba",
    "23b872dd7302113369cda2901243429419bec145408fa8b352b3dd92b66c680b",
    "a9059cbb2ab09eb219583f4a59a5d0623ade346d962bcd4e46b11da047c9049b",
    "70a08231b98ef4ca268c9cc3f6b4590e4bfec28280db06bb5d45e689f2a360be"
]

erc20_events = [
    "8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
    "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
]

erc721_sigs = [
    "70a08231b98ef4ca268c9cc3f6b4590e4bfec28280db06bb5d45e689f2a360be",
    "6352211e6566aa027e75ac9dbf2423197fbd9b82b9d981a3ab367d355866aa1c",
    "b88d4fde60196325a28bb7f99a2582e0b46de55b18761e960c14ad7a32099465",
    "42842e0eb38857a7775b4e7364b2775df7325074d088e7fb39590cd6281184ed",
    "23b872dd7302113369cda2901243429419bec145408fa8b352b3dd92b66c680b",
    "095ea7b334ae44009aa867bfb386f5c3b4b443ac6f0ee573fa91c4608fbadfba",
    "a22cb4651ab9570f89bb516380c40ce76762284fb1f21337ceaf6adab99e7d4a",
    "081812fc55e34fdc7cf5d8b5cf4e3621fa6423fde952ec6ab24afdc0d85c0b2e",
    "e985e9c5c6636c6879256001057b28ccac7718ef0ac56553ff9b926452cab8a3",
]

erc721_events = [
    "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    "8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
    "17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
]


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

    def get_args_types(self) -> str:
        return [i['type'] for i in self.args]

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
                _type: i['type'],
                name: i['name'],
                internal_type: i['internalType'] if 'internalType' in i else i['type']
            })

        for i in self.outputs:
            outputs.append({
                _type: i['type'],
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

    def __eq__(self, o) -> bool:
        if isinstance(o, Function):
            if o.signature == self.signature:
                return True
        elif isinstance(o, str):
            if o == self.name:
                return True

        return False

    def __hash__(self) -> int:
        return hash(self.signature)


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

        self.is_erc_20 = True
        self.is_erc_721 = True

        self.__determine_contract_type()

    def __load_events(self) -> [Event]:
        """
            Loads all events from the abi of the contract into the self.events property
        """

        events = []

        for row in self.abi:
            if row["type"] == "event":
                events.append(Event(row["name"], row["inputs"]))

        return events

    def __load_functions(self) -> [Function]:
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
            Again, taking advantage of address being unique. We avoid any complications with deep nested equalities from the events and functions this way
        """
        return isinstance(o, type(self)) and o.address == self.address

    def get_func_signatures(self) -> dict[str, [str]]:
        """ 
            Returns a list of all the function signatures for the contract
        """

        return {self.address: [i.signature for i in self.functions]}

    def get_function(self, name: str) -> Function:
        for f in self.functions:
            if f.name == name:
                return f

        raise FunctionNotFound

    def get_event(self, name: str) -> Event:
        for e in self.events:
            if e.name == name:
                return e

        raise EventNotFound

    def get_event_arg_lengths(self, event_sig : str) -> List[int]:
        lengths = []
        for e in self.events:
            if e.signature == event_sig:
                lengths = [ethtypes.get_type_length(i['type']) for i in e.args]

        return lengths

    def __determine_contract_type(self) -> None:
        erc_funcs = []
        erc_events = []

        for func in self.functions:
            if func.signature in erc20_sigs:
                erc_funcs.append(func.signature)
            elif func.signature in erc721_sigs:
                erc_funcs.append(func.signature)

        for event in self.events:
            if event.signature in erc20_events:
                erc_events.append(event.signature)
            elif event.signature in erc721_sigs:
                erc_funcs.append(func.signature)

        if erc_funcs != erc20_sigs or erc_events != erc20_events:
            self.is_erc_20 = False
        elif erc_funcs != erc721_sigs or erc_events != erc721_events:
            self.is_erc_721 = False

    def get_type(self) -> str:
        return "ERC20" if self.is_erc_20 else "ERC721" if self.is_erc_721 else ""
