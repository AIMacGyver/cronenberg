'''This module contains the main() function, which is the entry point for the
command line interface.'''

__version__ = '6.0.1'


def main():
    '''The entry point for Setuptools.

    ``cc`` is dispatched to Typer. ``raw``, ``mi``, and ``hal`` stay on mando.
    '''
    import os
    import sys

    from cronenberg.cli import cc_app, log_error, program

    if not sys.argv[1:]:
        sys.argv.append('-h')
    try:
        if sys.argv[1] == 'cc':
            prog = os.path.basename(sys.argv[0])
            cc_app(args=sys.argv[2:], prog_name=f'{prog} cc')
        else:
            program()
    except Exception as e:
        log_error(e)


if __name__ == '__main__':
    main()
