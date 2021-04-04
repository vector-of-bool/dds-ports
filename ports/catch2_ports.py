from pathlib import Path
from semver import VersionInfo

from dds_ports import auto, port, fs, github, util

CATCH_WITH_MAIN = '''
#pragma once

/**
 * The contents of this file are not part of the main Catch2 source distribution,
 * and are inserted as part of the dds port for Catch2.
 */

#define CATCH_CONFIG_MAIN
#include "./catch.hpp"

namespace Catch {

CATCH_REGISTER_REPORTER("console", ConsoleReporter)

}
'''


async def fixup_catch2(root: Path) -> None:
    await fs.move_files(
        files=root.glob('include/**/*'),
        into=root / 'include/catch2',
        whence=root / 'include',
    )
    await fs.copy_files(
        files=root.glob('include/**/*'),
        into=root / 'src',
        whence=root / 'include',
    )
    root.joinpath('include/catch2/catch_with_main.hpp').write_text(CATCH_WITH_MAIN)


async def all_ports() -> port.PortIter:
    tags = await github.get_repo_tags('catchorg', 'catch2')
    versions = ((tag, util.tag_as_version(tag)) for tag in tags)

    min_ver = VersionInfo(2, 12)
    max_ver = VersionInfo(2, 99999, 9999)
    return (
        auto.SimpleGitHubAdaptingPort(
            package_id=port.PackageID('catch2', version),
            owner='catchorg',
            repo='catch2',
            tag=tag,
            package_json={
                'name': 'catch2',
                'namespace': 'catch2',
                'depends': [],
            },
            library_json={
                'name': 'catch2',
                'uses': [],
            },
            fs_transform=fixup_catch2,
            try_build=True,
        ) for tag, version in versions  #
        if (version is not None and version >= min_ver and version < max_ver))  # pylint: disable=chained-comparison
