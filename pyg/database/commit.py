from typing import Optional

from .author import Author


class Commit:
    def __init__(
        self, parent: Optional[str], tree: str, author: Author, message: str
    ) -> None:
        self.oid = None
        self.parent: Optional[str] = parent
        self.tree = tree
        self.author = author
        self.message = message
        self.type = "commit"

    def __bytes__(self) -> bytes:
        lines = []
        lines.append(f"tree {self.tree}")
        if self.parent:
            lines.append(f"parent {self.parent}")
        lines.append(f"author {self.author}")
        lines.append(f"committer {self.author}")
        lines.append("")
        lines.append(self.message)

        return b"\n".join([bytes(line, "utf-8") for line in lines])
