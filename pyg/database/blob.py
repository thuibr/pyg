from typing import Optional


class Blob:
    def __init__(self, data: bytes) -> None:
        self.oid: Optional[str] = None
        self.data: bytes = data
        self.type = "blob"

    def __bytes__(self) -> bytes:
        return self.data
