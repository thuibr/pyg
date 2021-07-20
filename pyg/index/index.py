import struct
from contextlib import contextmanager
from hashlib import sha1
from os import stat_result
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Tuple

from lockfile import Lockfile

from .checksum import Checksum
from .entry import Entry, ENTRY_BLOCK, ENTRY_MIN_SIZE


class Index:
    HEADER_SIZE = 12
    HEADER_FORMAT = ">4s2I"
    SIGNATURE = "DIRC"
    VERSION = 2

    def __init__(self, pathname: Path) -> None:
        self.pathname: Path = pathname
        self.lockfile: Lockfile = Lockfile(pathname, as_bytes=True)
        self.clear()

    def clear(self) -> None:
        self.entries: Dict[Path, Entry] = {}
        self.changed: bool = False

    def add(self, pathname: Path, oid: Optional[str], stat: stat_result) -> None:
        """Queue entries for writing to index."""
        if not oid:
            raise Exception(f"Null OID for {pathname}")
        entry: Entry = Entry.new(pathname, oid, stat)
        self.store_entry(entry)
        self.changed = True

    def write_updates(self) -> bool:
        """Write entries to index."""
        if not self.lockfile.hold_for_update():
            return False

        self.begin_write()

        # Convert into a 12 byte header of ("DIRC", index version, # of entries)
        header: bytes = struct.pack(self.HEADER_FORMAT, b"DIRC", 2, len(self.entries))
        self.write(header)

        for key, entry in sorted(self.entries.items()):
            self.write(bytes(entry))

        self.finish_write()

        return True

    def begin_write(self) -> None:
        """Prepare the hash digest."""
        self.digest = sha1()

    def write(self, data: bytes) -> None:
        """Write the data to index. Update the hash."""
        self.lockfile.write(data)
        self.digest.update(data)

    def finish_write(self) -> None:
        """Write digest to index and commit it."""
        self.lockfile.write(self.digest.digest())
        self.lockfile.commit()

    def open_index_file(self) -> Optional[BinaryIO]:
        try:
            index_file = open(self.pathname, "rb")
            return index_file
        except FileNotFoundError:
            return None

    def read_header(self, reader: Checksum) -> int:
        """Read the header from the index."""
        data = reader.read(self.HEADER_SIZE)
        (sig_bytes, version, count) = struct.unpack(
            self.HEADER_FORMAT, data
        )  # type: Tuple[bytes, int, int]
        signature = sig_bytes.decode("utf-8")

        if str(signature) != self.SIGNATURE:
            raise Exception(
                f"Signature: expected '{self.SIGNATURE}' but found '{signature}'"
            )
        elif version != self.VERSION:
            raise Exception(
                f"Version: expected  '{self.VERSION}' but found '{version}'"
            )

        return count

    def store_entry(self, entry: Entry) -> None:
        """Store an entry in the dictionary of entries."""
        self.entries[entry.pathname] = entry

    def read_entries(self, reader: Checksum, count: int) -> None:
        """Read entries from index and load them into memory."""
        for c in range(0, count):
            # Read the minimum size that an entry could be
            entry: bytes = reader.read(ENTRY_MIN_SIZE)

            # Keep reading until reaching a null byte
            while entry[-1] != 0:
                # Entries are multiples of 8 bytes, so read 8 bytes at a time
                entry = entry + reader.read(ENTRY_BLOCK)

            self.store_entry(Entry.parse(entry))

    def load(self) -> None:
        """Load the existing index into memory."""
        self.clear()
        index_file = self.open_index_file()
        if index_file:
            try:
                reader: Checksum = Checksum(index_file)
                count = self.read_header(reader)
                self.read_entries(reader, count)
                reader.verify_checksum()
            finally:
                index_file.close()

    def load_for_update(self) -> bool:
        """Load the existing index into memory before update."""
        if self.lockfile.hold_for_update():
            self.load()
            return True
        return False
