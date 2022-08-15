from typing import Iterable, NamedTuple
import itertools

from dds_ports import github
from dds_ports.port import Port
from dds_ports.util import wait_all

from semver import VersionInfo


class NeoPackageSpec(NamedTuple):
    name: str
    min_version: VersionInfo
    max_version: VersionInfo | None


def legacy_all_neo_packages() -> Iterable[NeoPackageSpec]:
    version_zero = '0.0.0'
    pkgs = [
        ('neo-fun', '0.1.1', VersionInfo(0, 12)),
        ('neo-buffer', '0.2.1', None),
        ('neo-compress', version_zero, None),
        ('neo-url', version_zero, None),
        ('neo-sqlite3', '0.2.3', None),
        ('neo-io', version_zero, None),
        ('neo-http', version_zero, None),
        ('neo-concepts', '0.2.2', None),
    ]
    return (NeoPackageSpec(name, VersionInfo.parse(version), max) for name, version, max in pkgs)


def bpt_neo_packages() -> Iterable[NeoPackageSpec]:
    pkgs = [('neo-fun', '0.12.0', None)]
    return (NeoPackageSpec(name, VersionInfo.parse(min_version), max_version)
            for name, min_version, max_version in pkgs)


async def all_ports() -> Iterable[Port]:
    legacy_ports = await wait_all(
        github.native_dds_ports_for_github_repo(
            owner='vector-of-bool', repo=pkg.name, min_version=pkg.min_version, max_version=pkg.max_version, revision=2)
        for pkg in legacy_all_neo_packages())
    bpt_ports = await wait_all(
        github.native_bpt_ports_for_github_repo(
            owner='vector-of-bool', repo=pkg.name, min_version=pkg.min_version, max_version=pkg.max_version)
        for pkg in bpt_neo_packages())
    legacy_ports_1 = itertools.chain.from_iterable(legacy_ports)
    bpt_ports_1 = itertools.chain.from_iterable(bpt_ports)
    return itertools.chain(legacy_ports_1, bpt_ports_1)
