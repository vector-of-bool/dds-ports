from typing import Iterable, NamedTuple
from typing_extensions import Protocol
from pathlib import Path

from semver import VersionInfo

from dagon import task


class PackageID(NamedTuple):
    name: str
    version: VersionInfo
    revision: int

    def __str__(self) -> str:
        return f'{self.name}@{self.version}~{self.revision}'

    @staticmethod
    def parse(s: str) -> 'PackageID':
        name, verstr_1 = s.split('@')
        verstr, meta_ver = verstr_1.split('~')
        return PackageID(name, VersionInfo.parse(verstr), int(meta_ver))


class Port(Protocol):
    @property
    def package_id(self) -> PackageID:
        ...

    def make_prep_task(self) -> task.Task[Path]:
        ...


PortIter = Iterable[Port]
