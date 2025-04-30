# filescanner.py
"""
filescanner.py

High-performance recursive file and directory scanner.

Usage:
    from filescanner import scan
    for meta in scan("/path/to/root"):
        print(meta.path, meta.size)
"""

import os
from typing import Iterator, NamedTuple, Optional


__all__ = ["FileMeta", "scan"]


class FileMeta(NamedTuple):
    """
    Metadata for a file or directory entry.
    Attributes:
        path: Full path to the entry.
        name: Base name of the entry.
        size: Size in bytes (directories will report zero).
        mtime: Last modification time (as a POSIX timestamp).
        is_dir: True if this entry is a directory.
    """
    path: str
    name: str
    size: int
    mtime: float
    is_dir: bool


def scan(root: str, follow_symlinks: bool = False) -> Iterator[FileMeta]:
    """
    Recursively scan `root` and yield FileMeta for every entry.
    
    Args:
        root: Path to file or directory to scan.
        follow_symlinks: If True, will recurse into symlinked dirs
                         and report metadata for symlink targets.
                         Default is False (symlinks treated as files).
    
    Yields:
        FileMeta namedtuples for each file or directory.
    """
    try:
        with os.scandir(root) as it:
            for entry in it:
                try:
                    stat = entry.stat(follow_symlinks=follow_symlinks)
                except (PermissionError, FileNotFoundError):
                    # Skip entries we can't stat
                    continue

                meta = FileMeta(
                    path=entry.path,
                    name=entry.name,
                    size=stat.st_size if not entry.is_dir(follow_symlinks=follow_symlinks) else 0,
                    mtime=stat.st_mtime,
                    is_dir=entry.is_dir(follow_symlinks=follow_symlinks),
                )
                yield meta

                if entry.is_dir(follow_symlinks=follow_symlinks):
                    # Recurse into subdirectories
                    yield from scan(entry.path, follow_symlinks=follow_symlinks)
    except (NotADirectoryError, PermissionError, FileNotFoundError):
        # If root is a file, not a directory (or inaccessible), yield it directly
        try:
            stat = os.stat(root, follow_symlinks=follow_symlinks)
            yield FileMeta(
                path=root,
                name=os.path.basename(root),
                size=stat.st_size,
                mtime=stat.st_mtime,
                is_dir=False,
            )
        except Exception:
            return
