import os
from pathlib import Path
from typing import List, Optional


class Workspace:
    IGNORE = [".git"]

    def __init__(self, pathname: Path) -> None:
        self.pathname: Path = pathname

    def _list_files(self, path: Path) -> List[Path]:
        if path.is_dir():
            # Remove ignored filenames
            filenames = os.listdir(path)
            for i in self.IGNORE:
                if i in filenames:
                    filenames.remove(i)

            # Recursively find all files below directory
            # Does not include directories
            r = []
            for name in filenames:
                p = Path(path).joinpath(name)
                for f in self._list_files(p):
                    r.append(f)
            return r

        else:
            return [path.relative_to(self.pathname)]

    #    def _list_files(self, directory: Path) -> List[Path]:
    #        # Get all files in directory, removing ignored filenames
    #        filenames = os.listdir(directory)
    #        for i in self.IGNORE:
    #            if i in filenames:
    #                filenames.remove(i)
    #
    #        # Recursively find all files below directory
    #        r = []
    #        for name in filenames:
    #            path = Path(directory).joinpath(name)
    #
    #            if path.is_dir():
    #                # Recursively append all files below dir
    #                for f in self._list_files(path):
    #                    r.append(f)
    #            else:
    #                # Append file
    #                r.append(path.relative_to(self.pathname))
    #        return r

    def list_files(self, path: Optional[Path] = None) -> List[Path]:
        """Recursively list files and directories, ignoring certain files."""
        # Default to workspace
        if not path:
            path = self.pathname
        return self._list_files(path)

    def read_file(self, path: Path) -> bytes:
        """Read the contents of a file as bytes."""
        with open(path, "rb") as p:
            contents = p.read()
        return contents

    def stat_file(self, path: Path) -> os.stat_result:
        """Returns the file type and permissions of a file."""
        return Path(self.pathname).joinpath(path).stat()
