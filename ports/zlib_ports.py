import itertools
from pathlib import Path
from semver import VersionInfo

from dds_ports import auto, port, fs


async def fixup_zlib(root: Path) -> None:
    await fs.move_files(
        files=itertools.chain(root.glob('*.c'), root.glob('*.h')),
        into=root / 'src/',
        whence=root,
    )
    await fs.move_files(
        files=[root / 'src/zlib.h', root / 'src/zconf.h'],
        into=root / 'include',
        whence=root / 'src',
    )


async def all_ports() -> port.PortIter:
    tags_ver_strs = (
        ('v1.2.11', '1.2.11'),
        ('v1.2.10', '1.2.10'),
        ('v1.2.9', '1.2.9'),
        ('v1.2.8', '1.2.8'),
        ('v1.2.7.3', '1.2.7'),
        ('v1.2.6.1', '1.2.6'),
        ('v1.2.5.3', '1.2.5'),
        ('v1.2.4.5', '1.2.4'),
        ('v1.2.3.8', '1.2.3'),
        ('v1.2.2.4', '1.2.2'),
        ('v1.2.1.2', '1.2.1'),
        ('v1.2.0.8', '1.2.0'),
    )

    tags_vers = ((tag, VersionInfo.parse(s)) for tag, s in tags_ver_strs)

    return (auto.SimpleGitHubAdaptingPort(
        package_id=port.PackageID('zlib', version),
        owner='madler',
        repo='zlib',
        tag=tag,
        package_json={
            'name': 'zlib',
            'namespace': 'zlib',
            'depends': [],
        },
        library_json={
            'name': 'zlib',
            'uses': [],
        },
        fs_transform=fixup_zlib,
        try_build=True,
    ) for tag, version in tags_vers)
