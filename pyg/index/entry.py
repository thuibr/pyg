import struct
from io import BytesIO
from os import stat_result
from typing import Final, NamedTuple, Type, TypeVar
from pathlib import Path

REGULAR_MODE = 0o100644
EXECUTABLE_MODE = 0o100755

MAX_PATH_SIZE = 0xFFF

ENTRY_BLOCK = 8
ENTRY_MIN_SIZE = 64
ENTRY_FORMAT = ">10I20sH"

T = TypeVar("T", bound="Entry")


class Entry(NamedTuple):
    """
    Represents an entry in the index.

    32-bit ctime
    32-bit ctime_ns
    32-bit mtime
    32-bit mtime_ns
    32-bit dev
    32-bit ino
    32-bit mode
    32-bit uid
    32-bit gid
    32-bit file size
    160-bit SHA-1
    16-bit flags
    Null character
    """

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
        """Create a new entry."""
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
        mtime_ns = stat.st_mtime_ns - int(mtime * 1e9)

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
        """Parse a binary representation of an entry into an object."""
        with BytesIO(binary) as bio:
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
            ) = struct.unpack(ENTRY_FORMAT, bio.read(62))

            # Read variable-length path until null
            path = b"".join(iter(lambda: bio.read(1), b"\0")).decode("utf-8")

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

        # Pack values whose length is known
        s = struct.pack(
            ENTRY_FORMAT,
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
        )

        with BytesIO() as bio:
            # Write values whose length is known
            bio.write(s)

            # Write variable-length path
            bio.write(bin_path)

            # Need a null character
            bio.write(b"\0")

            # Pad to a multiple of ENTRY_BLOCK
            while len(bio.getvalue()) % ENTRY_BLOCK != 0:
                bio.write(b"\0")

            return bio.getvalue()
