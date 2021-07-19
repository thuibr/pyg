#!/usr/bin/env python

# TODO add a better argument parsing library

import os
import sys
import time
from pathlib import Path
from typing import Optional

from database.author import Author
from database.blob import Blob
from database.commit import Commit
from database.database import Database
from database.tree import Tree
from entry import Entry
from index.index import Index
from refs import Refs
from workspace import Workspace

command: str = sys.argv[1]

if command == "init":
    # Get path, defaulting to current working directory
    path: str = sys.argv[2] if len(sys.argv) > 2 else str(Path.cwd())

    # Setup absolute paths to working directory and Git directory
    root_path: Path = Path(path).resolve()
    git_path: Path = root_path.joinpath(".git")

    # Setup needed Git directories
    for d in ["objects", "refs"]:
        try:
            git_path.joinpath(d).mkdir(parents=True)
        except Exception as e:
            sys.stderr.write(f"fatal: {e}\n")
            sys.exit(1)

    print(f"Initialized empty Pyg repository in {git_path}")

elif command == "commit":
    # Setup paths to Git files and database
    root_path = Path.cwd()
    git_path = root_path.joinpath(".git")
    db_path: Path = git_path.joinpath("objects")

    # Setup handlers
    workspace: Workspace = Workspace(root_path)
    database: Database = Database(db_path)
    refs: Refs = Refs(git_path)

    # Process the list of paths to create Blobs and Entries
    entries = []
    for f in workspace.list_files():
        data: bytes = workspace.read_file(f)
        blob: Blob = Blob(data)

        database.store(blob)

        # Helps determine whether file is executable
        stat_mode: int = workspace.stat_file(f).st_mode

        if not isinstance(blob.oid, str):
            raise Exception(f"Blob {blob} does not have a valid oid")
        entry: Entry = Entry(f, blob.oid, stat_mode)
        entries.append(entry)

    # Build a nested Tree from the entries array
    root = Tree.build(entries)

    # Traverse the tree, finding and storing every subtree.
    # Iterate over all entries in the tree depth-first.
    # Calculate the object IDs and store the nodes in the database.
    # The lowest nodes need to be calculated and stored first
    # so that their parents' object IDs can be calculated.
    root.traverse(database.store)
    if not isinstance(root.oid, str):
        raise Exception(f"Tree {root} does not have oid")

    # Gather information for the commit
    parent: Optional[str] = refs.read_head()
    name: str = os.environ["GIT_AUTHOR_NAME"]
    email: str = os.environ["GIT_AUTHOR_EMAIL"]
    author: Author = Author(name, email, time.localtime())
    message: str = sys.stdin.read()

    # Create commit, store it, and update HEAD with the object ID of the commit
    commit: Commit = Commit(parent, root.oid, author, message)
    database.store(commit)
    refs.update_head(commit.oid)

    # Signify root-commit on first commit only
    is_root = "(root-commit) " if not parent else ""
    print("[{}{}] {}".format(is_root, commit.oid, message.split("\n", 1)[0]))

elif command == "add":
    # Setup paths to Git files and database
    root_path = Path.cwd()
    git_path = root_path.joinpath(".git")

    # Setup handlers
    workspace = Workspace(root_path)
    database = Database(git_path.joinpath("objects"))
    index: Index = Index(git_path.joinpath("index"))

    # Load the existing index into memory
    index.load_for_update()

    for path in sys.argv[2:]:
        # Recursively find all files in directory
        for pathname in workspace.list_files(Path(path).resolve()):
            # Get data needed to update database and index
            data = workspace.read_file(pathname)
            stat: os.stat_result = workspace.stat_file(pathname)

            # Update database and queue files in index
            blob = Blob(data)
            database.store(blob)
            index.add(pathname, blob.oid, stat)

    index.write_updates()


else:
    sys.stderr.write(f"pyg: '{command}' is not a command.\n")
    sys.exit(1)
