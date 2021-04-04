from typing import Iterable, NamedTuple
import itertools

from dds_ports import github
from dds_ports.port import Port
from dds_ports.util import wait_all

from semver import VersionInfo


class NeoPackageSpec(NamedTuple):
    name: str
    min_version: VersionInfo


def all_neo_packages() -> Iterable[NeoPackageSpec]:
    version_zero = '0.0.0'
    pairs = [
        ('neo-fun', '0.1.1'),
        ('neo-buffer', '0.2.1'),
        ('neo-compress', version_zero),
        ('neo-url', version_zero),
        ('neo-sqlite3', '0.2.3'),
        ('neo-io', version_zero),
        ('neo-http', version_zero),
        ('neo-concepts', '0.2.2'),
    ]
    return (NeoPackageSpec(name, VersionInfo.parse(version)) for name, version in pairs)


async def all_ports() -> Iterable[Port]:
    ports = await wait_all(
        github.native_dds_ports_for_github_repo(owner='vector-of-bool', repo=pkg.name, min_version=pkg.min_version)
        for pkg in all_neo_packages())
    return itertools.chain.from_iterable(ports)
