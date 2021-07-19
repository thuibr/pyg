import struct
from math import modf
from os import stat_result
from pathlib import Path
from typing import Final, List, Optional, Tuple, TypeVar, Type

T = TypeVar("T", bound="Entry")


class Entry:
    REGULAR_MODE: Final = 0o100644
    EXECUTABLE_MODE: Final = 0o100755
    MAX_PATH_SIZE: Final = 0xFFF
    ENTRY_BLOCK: Final = 8
    ENTRY_MIN_SIZE: Final = 64
    ENTRY_FORMAT: Final = ">10I20sH%dsx"

    def __init__(
        self, pathname: Path, oid: str, stat: Optional[stat_result] = None
    ) -> None:
        self.pathname: Path = pathname
        self.oid: str = oid
        if stat:
            # Check if user has permissions to execute the file
            if stat.st_mode & 0o000100 != 0:
                self.mode: int = self.EXECUTABLE_MODE
            else:
                self.mode = self.REGULAR_MODE

            # Contains length of path or a maximum length
            self.flags = min([len(bytes(pathname)), self.MAX_PATH_SIZE])

            # TODO may not match behavior on Windows
            # Time in seconds and nanoseconds
            # The value encoded for *_ns needs to exclude the seconds
            self.ctime: int = int(stat.st_ctime)
            self.ctime_ns: int = stat.st_ctime_ns - int(self.ctime * 1e9)
            self.mtime: int = int(stat.st_mtime)
            self.mtime_ns: int = stat.st_mtime_ns - int(self.ctime * 1e9)

            self.dev: int = stat.st_dev
            self.ino: int = stat.st_ino
            self.uid: int = stat.st_uid
            self.gid: int = stat.st_gid
            self.size: int = stat.st_size

    @classmethod
    def parse(cls: Type[T], binary: bytes) -> T:
        """Parse a binary representation of entry."""
        # First need to find out length of the path
        # Fortunately, we know where this gets stored
        path_len: int = binary[61]

        # Define encoding, dynamically setting length of path array
        encoding: str = cls.ENTRY_FORMAT % (path_len,)

        # Unpack values from binary
        (
            ctime,
            ctime_ns,
            mtime,
            mtime_ns,
            dev,
            ino,
            mode,
            uid,
            gid,
            size,
            oid,
            flags,
            path,
        ) = struct.unpack(encoding, binary)

        # Define new class
        c: T = cls(Path(path), oid.hex())
        c.ctime = ctime
        c.ctime_ns = ctime_ns
        c.mtime = mtime
        c.mtime_ns = mtime_ns
        c.dev = dev
        c.ino = ino
        c.mode = mode
        c.uid = uid
        c.gid = gid
        c.size = size
        c.oid = oid
        c.flags = flags

        return c

    def __bytes__(self) -> bytes:
        """Return binary representation of entry."""
        bin_path: bytes = bytes(self.pathname)
        bin_oid: bytes = bytes.fromhex(self.oid[:40])

        # Format for storing entry in the index:
        # - 10 32-bit unsigned big-endian integers (derived from stat)
        # - 40-character hex string packed into 20 bytes (oid)
        # - 16-bit unsigned big-endian integer (flags)
        # - Variable-length path
        # - null-terminated
        s = struct.pack(
            # Define encoding, dynamically setting length of path array
            self.ENTRY_FORMAT % (len(bin_path),),
            self.ctime,
            self.ctime_ns,
            self.mtime,
            self.mtime_ns,
            self.dev,
            self.ino,
            self.mode,
            self.uid,
            self.gid,
            self.size,
            bin_oid,
            self.flags,
            bin_path,
        )

        # Pad to a multiple of ENTRY_BLOCK
        while len(s) % self.ENTRY_BLOCK != 0:
            s += b"\0"

        return s
