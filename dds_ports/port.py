from typing import Iterable, NamedTuple, AsyncContextManager
from typing_extensions import Protocol
from pathlib import Path

from semver import VersionInfo


class PackageID(NamedTuple):
    name: str
    version: VersionInfo

    def __str__(self) -> str:
        return f'{self.name}@{self.version}'

    @staticmethod
    def parse(s: str) -> 'PackageID':
        name, verstr = s.split('@')
        return PackageID(name, VersionInfo.parse(verstr))


class Port(Protocol):
    @property
    def package_id(self) -> PackageID:
        ...

    def prepare_sdist(self) -> AsyncContextManager[Path]:
        ...


PortIter = Iterable[Port]
