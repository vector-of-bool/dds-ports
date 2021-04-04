import asyncio
from typing import Iterable
from pathlib import Path
import subprocess

from .port import PackageID


class RepositoryAccess:
    def __init__(self, dirpath: Path, pkgs: Iterable[PackageID]) -> None:
        self._dirpath = dirpath
        self._pkgs = set(pkgs)
        self._lock = asyncio.Lock()

    @property
    def packages(self) -> Iterable[PackageID]:
        """Packages in the repository"""
        return self._pkgs

    @property
    def database_path(self) -> Path:
        return self._dirpath / 'repo.db'

    @property
    def directory(self) -> Path:
        """Directory root of the repository"""
        return self._dirpath

    @staticmethod
    async def open(dirpath: Path) -> 'RepositoryAccess':
        lines = subprocess.check_output(['./dds', 'repoman', 'ls', str(dirpath)]).strip().splitlines()
        return RepositoryAccess(dirpath, (PackageID.parse(l.decode()) for l in lines))
