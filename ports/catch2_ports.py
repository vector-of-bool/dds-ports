from pathlib import Path
import itertools
import json

from semver import VersionInfo

from dds_ports import auto, port, fs, github, util, crs

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


async def fixup_catch2_v3(root: Path) -> None:
    await fs.move_files(
        files=[root / 'src/catch2/internal/catch_main.cpp'],
        into=root / 'libs/main/',
        whence=root,
    )
    root.joinpath('libs/main/library.jsonc').write_text(
        json.dumps({
            'name': 'catch2_with_main',
            'uses': ['catch2/catch2'],
        }))


async def all_ports() -> port.PortIter:
    tags = await github.get_repo_tags('catchorg', 'catch2')
    versions = list((tag, util.tag_as_version(tag)) for tag in tags)

    min_ver = VersionInfo(2, 12)
    max_ver = VersionInfo(2, 99999, 9999)
    meta_version = 1
    v2 = (
        auto.SimpleGitHubAdaptingPort(
            package_id=port.PackageID('catch2', version, meta_version),
            owner='catchorg',
            repo='catch2',
            tag=tag,
            crs_json=crs.simple_placeholder_json('catch2'),
            fs_transform=fixup_catch2,
            try_build=True,
        ) for tag, version in versions  #
        if (version is not None and version >= min_ver and version < max_ver))  # pylint: disable=chained-comparison
    v3_placeholder = crs.simple_placeholder_json('catch2')
    v3_placeholder['libraries'].append({
        'name': 'main',
        'path': 'libs/main',
        'depends': [],
        'uses': [{
            'lib': 'catch2/catch2',
            'for': 'lib'
        }]
    })
    v3 = (
        auto.SimpleGitHubAdaptingPort(
            package_id=port.PackageID('catch2', version, meta_version),
            owner='catchorg',
            repo='catch2',
            tag=tag,
            crs_json=v3_placeholder,
            fs_transform=fixup_catch2_v3,
            try_build=True,
        ) for tag, version in versions  #
        if (version and version >= VersionInfo.parse('3.0.0-preview2')))
    return itertools.chain(v2, v3)
