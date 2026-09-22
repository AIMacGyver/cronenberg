'''This module contains the main() function, which is the entry point for the
command line interface.'''

__version__ = '6.0.1'


def main():
    '''The entry point for Setuptools.

    ``cc``, ``raw``, ``mi``, and ``hal`` are dispatched to Typer.
    '''
    import os
    import sys

    from cronenberg.cli import cc_app, hal_app, log_error, mi_app, program, raw_app

    if not sys.argv[1:]:
        sys.argv.append('-h')
    try:
        command = sys.argv[1]
        prog = os.path.basename(sys.argv[0])
        apps = {'cc': cc_app, 'raw': raw_app, 'mi': mi_app, 'hal': hal_app}
        if command in apps:
            apps[command](args=sys.argv[2:], prog_name=f'{prog} {command}')
        else:
            program()
    except Exception as e:
        log_error(e)


if __name__ == '__main__':
    main()
