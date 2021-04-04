import itertools
from typing import Iterable

from semver import VersionInfo

from dds_ports import github, util, port


async def all_ports() -> Iterable[port.Port]:
    return itertools.chain.from_iterable(await util.wait_all((
        github.native_dds_ports_for_github_repo(
            owner='vector-of-bool',
            repo='semver',
            min_version=VersionInfo(0, 2, 2),
        ),
        github.native_dds_ports_for_github_repo(
            owner='vector-of-bool',
            repo='json5',
            pkg_name='vob-json5',
            min_version=VersionInfo(0, 1, 5),
        ),
        github.native_dds_ports_for_github_repo(
            owner='vector-of-bool',
            repo='pubgrub',
            min_version=VersionInfo(0, 2, 1),
        ),
        github.native_dds_ports_for_github_repo(
            owner='vector-of-bool',
            repo='semester',
            pkg_name='vob-semester',
        ),
    )))
