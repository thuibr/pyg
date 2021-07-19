from hashlib import sha1
from typing import BinaryIO


class Checksum:
    class EndOfFile(Exception):
        pass

    CHECKSUM_SIZE = 20

    def __init__(self, f: BinaryIO) -> None:
        self.f = f
        self.digest = sha1()

    def read(self, size: int) -> bytes:
        data: bytes = self.f.read(size)

        if len(data) != size:
            raise self.EndOfFile("Unexpected end-of-file while reading index")

        self.digest.update(data)
        return data

    def verify_checksum(self) -> None:
        s = self.f.read(self.CHECKSUM_SIZE)

        if s != self.digest.digest():
            raise Exception("Checksum does not match value stored on disk")
