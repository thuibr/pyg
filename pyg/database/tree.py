from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Type, Union

from .blob import Blob
from .commit import Commit

from entry import Entry

T = TypeVar("T", bound="Tree")


class Tree:
    def __init__(self) -> None:
        self.oid = None
        self.entries: Dict[str, Union[Entry, Tree, None]] = OrderedDict()
        self.type = "tree"

    def __str__(self) -> str:
        return f"{self.mode} {self.type} {self.oid}"

    def __bytes__(self) -> bytes:
        """
        Returns Tree in the serialized form that Git stores on disk.
        """
        # Serialize the list of objects in the tree
        bytes_entries: List[bytes] = []
        for name, entry in self.entries.items():
            if not entry:
                raise Exception(f"Entry is null")

            # File mode
            bytes_mode = bytes(entry.mode, "utf-8")

            # File name
            bytes_name = bytes(name, "utf-8")

            # Object ID (first 40 characters)
            if not isinstance(entry.oid, str):
                raise Exception(f"Entry {entry} does not have a valid oid: {entry.oid}")
            bytes_oid = bytes.fromhex(entry.oid[:40])

            # Serialization format of an entry: b"<mode> <name>\0<oid>"
            bytes_entry = bytes_mode + b" " + bytes_name + b"\0" + bytes_oid

            bytes_entries.append(bytes_entry)

        # Return the list of serialized objects concatenated together
        return b"".join(bytes_entries)

    @classmethod
    def build(cls: Type[T], entries: List[Entry]) -> T:
        """Constructs a set of Tree objects that reflect the entries list."""
        entries.sort(key=lambda x: x.pathname)
        root: T = cls()

        for entry in entries:
            parent_directories: List[Path] = entry.parent_directories()
            root._add_entry(parent_directories, entry)

        return root

    def _add_entry(self, parents: List[Path], entry: Entry) -> None:
        """Inserts Entry at the right point in the tree."""

        # Add entry to tree if it has no parent directories
        # Otherwise, add a tree to the tree and recurse
        if not parents:
            name: str = entry.name
            self.entries[name] = entry
        else:
            # Get or create the tree for the top-most directory of parents
            name = parents[0].name
            tree: Union[Entry, Tree, None] = self.entries.get(name)
            if not tree:
                tree = Tree()
                self.entries[name] = tree
            elif not isinstance(tree, Tree):
                raise Exception(f"{tree} is not a Tree")

            # Call add_entry again, excluding the first element of parents
            tree._add_entry(parents[1:], entry)

    def traverse(self, store: Callable[[Any], None]) -> None:
        """
        Depth-first iteration over all self.entries. Call function on each node.
        """
        # Iterate over children first
        for name, entry in self.entries.items():
            # Has children
            if isinstance(entry, Tree):
                entry.traverse(store)
            # Leaf node
            elif isinstance(entry, Blob):
                store(entry)
        # Then store current node
        store(self)

    @property
    def mode(self) -> str:
        """Returns the mode that Git uses to serialize and store a Tree."""
        return Entry.DIRECTORY_MODE
