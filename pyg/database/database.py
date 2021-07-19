import random
import string
import zlib
from hashlib import sha1
from pathlib import Path
from typing import BinaryIO, Union

from .blob import Blob
from .commit import Commit
from .tree import Tree


class Database:
    def __init__(self, pathname: Path) -> None:
        self.pathname: Path = pathname

    def store(self, obj: Union[Blob, Commit, Tree]) -> None:
        string: bytes = bytes(obj)
        length: str = str(len(string))
        header: str = f"{obj.type} {length}"
        content: bytes = bytes(header, "utf-8") + b"\0" + string

        obj.oid = sha1(content).hexdigest()
        self._write_object(obj.oid, content)

    def _write_object(self, oid: str, content: bytes) -> None:
        # Create the path of the object on disk
        object_path: Path = Path(self.pathname).joinpath(oid[0:2]).joinpath(oid[2:])

        # Save time writing the object if it already exists on disk
        if object_path.exists():
            return

        # Write to a temporary file so that the "write" to the object's path is atomic
        dirname: Path = object_path.parent
        temp_path: Path = dirname.joinpath(self._generate_temp_name())
        try:
            f: BinaryIO = open(temp_path, "xb")
        except FileNotFoundError:
            Path(dirname).mkdir()
            f = open(temp_path, "xb")

        # Write compressed object to temporary file using fastest speed (level=1)
        compressed: bytes = zlib.compress(content, level=1)
        f.write(compressed)
        f.close()

        # Atomically "write" to object's path
        temp_path.rename(object_path)

    def _generate_temp_name(self) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=6))
