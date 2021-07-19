import struct
from os import stat_result
from typing import Final, NamedTuple, Type, TypeVar
from pathlib import Path

REGULAR_MODE: Final = 0o100644
EXECUTABLE_MODE: Final = 0o100755
MAX_PATH_SIZE: Final = 0xFFF

# Format for storing entry in the index:
# - 10 32-bit unsigned big-endian integers (derived from stat)
# - 40-character hex string packed into 20 bytes (oid)
# - 16-bit unsigned big-endian integer (flags)
# - Variable-length path
# - null-terminated
ENTRY_BLOCK: Final = 8
ENTRY_MIN_SIZE: Final = 64
ENTRY_FORMAT: Final = ">10I20sH%dsx"

T = TypeVar("T", bound="Entry")


class Entry(NamedTuple):
    pathname: Path
    oid: str
    mode: int
    flags: int
    ctime: int
    ctime_ns: int
    mtime: int
    mtime_ns: int
    dev: int
    ino: int
    uid: int
    gid: int
    size: int

    @classmethod
    def new(cls: Type[T], pathname: Path, oid: str, stat: stat_result) -> T:
        """Create a new entry object."""
        # Check if user has permissions to execute the file
        mode = REGULAR_MODE if stat.st_mode & 0o000100 == 0 else EXECUTABLE_MODE

        # Contains length of path or a maximum length
        flags = min([len(bytes(pathname)), MAX_PATH_SIZE])

        # TODO may not match behavior on Windows
        # Time in seconds and nanoseconds
        # The value encoded for *_ns needs to exclude the seconds
        ctime = int(stat.st_ctime)
        ctime_ns = stat.st_ctime_ns - int(ctime * 1e9)
        mtime = int(stat.st_mtime)
        mtime_ns = stat.st_mtime_ns - int(ctime * 1e9)

        return cls(
            pathname=pathname,
            oid=oid,
            mode=mode,
            flags=flags,
            ctime=ctime,
            ctime_ns=ctime_ns,
            mtime=mtime,
            mtime_ns=mtime_ns,
            dev=stat.st_dev,
            ino=stat.st_ino,
            uid=stat.st_uid,
            gid=stat.st_gid,
            size=stat.st_size,
        )

    @classmethod
    def parse(cls: Type[T], binary: bytes) -> T:
        """Parse a binary representation of entry."""
        # Define encoding based on variable length of path
        path_len: int = binary[61]
        encoding: str = ENTRY_FORMAT % (path_len,)

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
            hex_oid,
            flags,
            path,
        ) = struct.unpack(encoding, binary)

        # Perform additional processing
        pathname: Path = Path(path)
        oid: str = hex_oid.hex()

        return cls(
            pathname=pathname,
            oid=oid,
            mode=mode,
            flags=flags,
            ctime=ctime,
            ctime_ns=ctime_ns,
            mtime=mtime,
            mtime_ns=mtime_ns,
            dev=dev,
            ino=ino,
            uid=uid,
            gid=gid,
            size=size,
        )

    def __bytes__(self) -> bytes:
        """Return binary representation of entry."""

        # Perform preprocessing
        bin_path: bytes = bytes(self.pathname)
        bin_oid: bytes = bytes.fromhex(self.oid[:40])

        s = struct.pack(
            # Define encoding, dynamically setting length of path array
            ENTRY_FORMAT % (len(bin_path),),
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
        while len(s) % ENTRY_BLOCK != 0:
            s += b"\0"

        return s
