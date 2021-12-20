from typing import Iterable, NamedTuple, AsyncContextManager
from typing_extensions import Protocol
from pathlib import Path

from semver import VersionInfo


class PackageID(NamedTuple):
    name: str
    version: VersionInfo
    meta_version: int

    def __str__(self) -> str:
        return f'{self.name}@{self.version}~{self.meta_version}'

    @staticmethod
    def parse(s: str) -> 'PackageID':
        name, verstr_1 = s.split('@')
        verstr, meta_ver = verstr_1.split('~')
        return PackageID(name, VersionInfo.parse(verstr), int(meta_ver))


class Port(Protocol):
    @property
    def package_id(self) -> PackageID:
        ...

    def prepare_sdist(self) -> AsyncContextManager[Path]:
        ...


PortIter = Iterable[Port]
