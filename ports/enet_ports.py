from pathlib import Path

from dds_ports import port, auto, fs

ENET_CONFIG = '''
#pragma once

/**
 * The contents of this file are not part of the main ENet source distribution,
 * and are inserted as part of the dds port for ENet.
 */

#if __has_include(<enet.tweaks.h>)
    #include <enet.tweaks.h>
#endif

#if ENET_BUILDING_LIB

    #if __has_include(<enet.internal-tweaks.h>)
        #include <enet.internal-tweaks.h>
    #endif

    #if __has_include(<fcntl.h>)
        #define HAS_FCNTL
    #endif

    #if __has_include(<poll.h>)
        #define HAS_POLL
    #endif

    #if __unix__
        #define HAS_SOCKLEN_T
        #define HAS_MSGHDR_FLAGS 1
    #endif

    #if __unix__ || _WIN32
        #define HAS_GETADDRINFO 1
        #define HAS_GETNAMEINFO 1
        #define HAS_INET_PTON 1
        #define HAS_INET_NTOP 1
    #endif

#endif  // ENET_BUILDING_LIB
'''


async def fixup_enet(dirpath: Path) -> None:
    await fs.move_files(
        whence=dirpath,
        files=dirpath.glob('*.c'),
        into=dirpath / 'src',
    )
    dirpath.joinpath('include/enet/config.h').write_text(ENET_CONFIG)
    main_h = dirpath / 'include/enet/enet.h'
    main_h_content = main_h.read_text()
    main_h_content = '#include <enet/config.h>\n' + main_h_content
    main_h.write_text(main_h_content)


async def all_ports() -> port.PortIter:
    return await auto.enumerate_simple_github(
        owner='lsalzman',
        repo='enet',
        package_name='enet',
        library_name='enet',
        fs_transform=fixup_enet,
    )
