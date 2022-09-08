import enum
from errors import TypeNotFound

types = {
    "int8": 8,
    "uint8": 8,
    "int16": 16,
    "uint16": 16,
    "int32": 32,
    "uint32": 32,
    "int64": 64,
    "uint64": 64,
    "int128": 128,
    "uint128": 128,
    "int256": 256,
    "uint256": 256,
    "bytes1": 1,
    "bytes2": 2,
    "bytes3": 3,
    "bytes4": 4,
    "bytes5": 5,
    "bytes6": 6,
    "bytes7": 7,
    "bytes8": 8,
    "bytes9": 9,
    "bytes10": 10,
    "bytes11": 11,
    "bytes12": 12,
    "bytes13": 13,
    "bytes14": 14,
    "bytes15": 15,
    "bytes16": 16,
    "bytes17": 17,
    "bytes18": 18,
    "bytes19": 19,
    "bytes20": 20,
    "bytes21": 21,
    "bytes22": 22,
    "bytes23": 23,
    "bytes24": 24,
    "bytes25": 25,
    "bytes26": 26,
    "bytes27": 27,
    "bytes28": 28,
    "bytes29": 29,
    "bytes30": 30,
    "bytes31": 31,
    "bytes32": 32,
    "address": 64,
}


def get_type_length(_type: str) -> int:
    length = types.get(_type)

    if length is None:
        raise TypeNotFound

    return length
