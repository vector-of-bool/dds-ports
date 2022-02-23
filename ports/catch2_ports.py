from pathlib import Path
import itertools

from semver import VersionInfo

from dds_ports import auto, port, fs, github, util, crs

CATCH2_V2_HEADER_PREFIX = '''
#ifndef CATCH2_DDS_WRAPPED_INCLUDED
#define CATCH2_DDS_WRAPPED_INCLUDED
#if defined(__has_include)
    #if __has_include(<catch2.tweaks.hpp>)
        #include <catch2.tweaks.hpp>
    #endif
#endif
'''

CATCH2_V2_HEADER_SUFFIX = '''
#endif  // CATCH2_DDS_WRAPPED_INCLUDED
# '''

CATCH_WITH_MAIN = '''
/**
 * The contents of this file are not part of the main Catch2 source distribution,
 * and are inserted as part of the dds port for Catch2.
 */

#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
'''


async def fixup_catch2_v2(root: Path) -> None:
    await fs.remove_directory(root / 'include')
    if root.joinpath('src').exists():
        await fs.remove_directory(root / 'src')
    await fs.move_files(
        files=root.glob('single_include/**/*'),
        into=root / 'src/',
        whence=root / 'single_include/',
    )
    main_header = root / 'src/catch2/catch.hpp'
    main_header.write_text(  #
        CATCH2_V2_HEADER_PREFIX +  #
        main_header.read_text()  #
        + CATCH2_V2_HEADER_SUFFIX,  #
        encoding='utf-8',
    )
    main_src = root / 'libs/main/src'
    main_src.mkdir(parents=True)
    main_src.joinpath('catch_with_main.cpp').write_text(CATCH_WITH_MAIN)


async def fixup_catch2_v3(root: Path) -> None:
    await fs.move_files(
        files=[root / 'src/catch2/internal/catch_main.cpp'],
        into=root / 'libs/main/',
        whence=root,
    )


async def all_ports() -> port.PortIter:
    tags = await github.get_repo_tags('catchorg', 'catch2')
    versions = list((tag, util.tag_as_version(tag)) for tag in tags)

    min_ver = VersionInfo(2, 12)
    max_ver = VersionInfo(2, 99999, 9999)
    meta_version = 1
    crs_placeholder = crs.simple_placeholder_json('catch2')
    crs_placeholder['libraries'].append({
        'name': 'main',
        'path': 'libs/main',
        'dependencies': [],
        'using': [{
            'lib': 'catch2',
            'for': 'lib',
        }],
    })
    v2 = (
        auto.SimpleGitHubAdaptingPort(
            package_id=port.PackageID('catch2', version, meta_version),
            owner='catchorg',
            repo='catch2',
            tag=tag,
            crs_json=crs_placeholder,
            fs_transform=fixup_catch2_v2,
            try_build=True,
        ) for tag, version in versions  #
        if (version is not None and version >= min_ver and version < max_ver))  # pylint: disable=chained-comparison
    v3 = (
        auto.SimpleGitHubAdaptingPort(
            package_id=port.PackageID('catch2', version, meta_version),
            owner='catchorg',
            repo='catch2',
            tag=tag,
            crs_json=crs_placeholder,
            fs_transform=fixup_catch2_v3,
            try_build=True,
        ) for tag, version in versions  #
        if (version and version >= VersionInfo.parse('3.0.0-preview2')))
    return itertools.chain(v2, v3)
