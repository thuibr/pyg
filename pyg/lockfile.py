from pathlib import Path
from typing import Any, AnyStr, IO, Optional

# TODO create context manager
class Lockfile:
    class MissingParent(Exception):
        pass

    class NoPermission(Exception):
        pass

    class StaleLock(Exception):
        pass

    def __init__(self, path: Path, as_bytes: bool = False) -> None:
        self.file_path: Path = path
        self.lock_path: Path = self.file_path.with_suffix(".lock")
        self.lock: Optional[IO[Any]] = None
        self.as_bytes = as_bytes

    def hold_for_update(self) -> bool:
        """
        Attemps to claim the lock file.

        Returns True if successful or False if lock has already been claimed.
        """
        try:
            if not self.lock:
                self.lock = open(self.lock_path, "xb" if self.as_bytes else "x")
            return True
        except FileExistsError:
            return False
        except FileNotFoundError as e:
            raise self.MissingParent(e)
        except PermissionError as e:
            raise self.NoPermission(e)

    def write(self, string: AnyStr) -> None:
        """Writes string to file."""
        if not self.lock:
            raise self.StaleLock(f"Not holding lock on file: {self.lock_path}")

        self.lock.write(string)

    def commit(self) -> None:
        """Closes and renames file."""
        if not self.lock:
            raise self.StaleLock(f"Not holding lock on file: {self.lock_path}")

        self.lock.close()
        self.lock_path.rename(self.file_path)
        self.lock = None
