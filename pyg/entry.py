from pathlib import Path
from typing import List


class Entry:

    REGULAR_MODE = "100644"
    EXECUTABLE_MODE = "100755"
    DIRECTORY_MODE = "40000"

    def __init__(self, pathname: Path, oid: str, stat: int) -> None:
        self.pathname = Path(pathname)
        self.oid = oid
        self.stat = stat

    def __str__(self) -> str:
        return f"{self.mode} {self.oid} {self.pathname}"

    @property
    def mode(self) -> str:
        """Returns the mode of the file, either regular or executable."""

        # Check if user has permissions to execute the file
        if self.stat & 0o000100 != 0:
            return self.EXECUTABLE_MODE

        return self.REGULAR_MODE

    def parent_directories(self) -> List[Path]:
        """Return all parent directories of the entry's name in descnding order."""
        p = Path(self.pathname)
        # Skip last item, the entry's path itself
        q = list(p.parents)[:-1]
        q.reverse()
        return q

    @property
    def name(self) -> str:
        """
        Returns the last component of the entry's pathname.

        For example, for 'foo/bar/baz.txt', this method will
        return 'baz.txt'. Written to match pathlib.Path.name().
        """
        return self.pathname.name
