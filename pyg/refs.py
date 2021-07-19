from pathlib import Path
from typing import Optional

from lockfile import Lockfile


class Refs:
    class LockDenied(Exception):
        pass

    def __init__(self, pathname: Path) -> None:
        self.pathname = pathname
        self.head_path: Path = Path(self.pathname).joinpath("HEAD")

    def update_head(self, oid: str) -> None:
        """Updates the contents of the HEAD file."""
        lockfile: Lockfile = Lockfile(self.head_path)

        if not lockfile.hold_for_update():
            raise self.LockDenied(f"Could not acquire lock on file: {self.head_path}")

        lockfile.write(oid)
        lockfile.write("\n")
        lockfile.commit()

    def read_head(self) -> Optional[str]:
        """Reads the contents of the HEAD file if it exists."""
        if self.head_path.exists():
            with open(self.head_path, "r") as f:
                return f.read().strip()
        return None
