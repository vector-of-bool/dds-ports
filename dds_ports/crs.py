from __future__ import annotations

from typing import Optional, Iterable
from typing_extensions import Literal, TypedDict
from pathlib import Path
import json
import re

import semver

CRS_LibraryUses = TypedDict('CRS_LibraryUses', {
    'lib': str,
    'for': Literal['lib', 'app', 'test'],
})
CRS_DepVersionRange = TypedDict('CRS_DepVersionRange', {
    'low': str,
    'high': str,
})
CRS_Dependency = TypedDict('CRS_Dependency', {
    'name': str,
    'for': Literal['lib', 'app', 'test'],
    'versions': 'list[CRS_DepVersionRange]',
    'uses': 'list[str]',
})
CRS_Library = TypedDict('CRS_Library', {
    'path': str,
    'name': str,
    'depends': 'list[CRS_Dependency]',
    'uses': 'list[CRS_LibraryUses]',
})

CRS_JSON = TypedDict(
    'CRS_JSON', {
        'name': str,
        'version': str,
        'meta_version': int,
        'namespace': str,
        'libraries': 'list[CRS_Library]',
        'crs_version': Literal[1],
    })

_DEP_SPLIT_RE = re.compile(r'^(.+?)([@^~+])(.+)$')


def convert_dep_str(dep: str, *, uses: Iterable[str] = ()) -> CRS_Dependency:
    mat = _DEP_SPLIT_RE.match(dep)
    assert mat, dep
    name, tag, version_str = mat.groups()
    version = semver.VersionInfo.parse(version_str)
    hi_version = semver.VersionInfo(0)
    if tag == '@':
        hi_version = version.bump_patch()
    elif tag == '~':
        hi_version = version.bump_major()
    elif tag == '^':
        hi_version = version.bump_major()
    elif tag == '+':
        hi_version = semver.VersionInfo(999999)
    else:
        assert 0, (dep, tag)
    return {
        'name': str(name),
        'for': 'lib',
        'versions': [{
            'low': str(version),
            'high': str(hi_version),
        }],
        'uses': list(uses),
    }


def write_crs_file(dirpath: Path, content: CRS_JSON) -> Path:
    dest = dirpath / 'pkg.json'
    dest.write_text(json.dumps(content, indent=2))
    return dest


def simple_placeholder_json(library: str, *, namespace: Optional[str] = None) -> CRS_JSON:
    namespace = namespace or library
    return {
        'name': '[placeholder]',
        'version': '[placeholder]',
        'meta_version': -1,
        'namespace': namespace,
        'libraries': [{
            'name': library,
            'path': '.',
            'uses': [],
            'depends': [],
        }],
        'crs_version': 1,
    }
