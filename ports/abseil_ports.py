import itertools
from pathlib import Path

from semver import VersionInfo

from dds_ports import auto, port, fs


async def fixup_abseil(root: Path) -> None:
    await fs.move_files(
        files=root.glob('absl/**/*'),
        whence=root,
        into=root / 'src',
    )
    # Files that should not be included:
    rm_patterns = (
        '*_test.c*',
        '*_testing.c*',
        '*_benchmark.c*',
        '*_benchmarks.c*',
        'benchmarks.c*',
        '*_test_common.c*',
        'mocking_*.c*',
        'test_util.cc',
        'mutex_nonprod.cc',
        'named_generator.cc',
        'print_hash_of.cc',
        '*_gentables.cc',
    )
    await fs.remove_files(itertools.chain.from_iterable(root.joinpath('src/absl').rglob(pat) for pat in rm_patterns))


async def all_ports() -> port.PortIter:
    tags = [
        ('20200923.2', '2020.9.23'),
        ('20200225.3', '2020.2.25'),
        ('20190808.1', '2019.8.8'),
    ]

    return (auto.SimpleGitHubAdaptingPort(
        package_id=port.PackageID('abseil', VersionInfo.parse(version_str)),
        owner='abseil',
        repo='abseil-cpp',
        tag=tag,
        package_json={
            'name': 'abseil',
            'namespace': 'abseil',
            'depends': [],
        },
        library_json={
            'name': 'abseil',
            'uses': [],
        },
        fs_transform=fixup_abseil,
        try_build=False,
    ) for tag, version_str in tags)
