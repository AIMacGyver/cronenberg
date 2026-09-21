'''This module contains various utility functions used in the CLI interface.
Attributes:
    _encoding (str): encoding with all files will be opened. Configured by
    environment variable RADONFILESENCODING
'''

import fnmatch
import os
import platform
import sys
import xml.etree.ElementTree as et
from contextlib import contextmanager

from radon.cli.colors import BRIGHT, LETTERS_COLORS, RANKS_COLORS, RESET, TEMPLATE
from radon.complexity import cc_rank
from radon.visitors import Function

# PyPy doesn't support encoding parameter in `open()` function and works with
# UTF-8 encoding by default
if platform.python_implementation() == 'PyPy':

    @contextmanager
    def _open(path):
        '''Mock of the built-in `open()` function. If `path` is `-` then
        `sys.stdin` is returned.
        '''
        if path == '-':
            yield sys.stdin
        else:
            with open(path) as f:
                yield f


else:
    default_encoding = 'utf-8'
    # Add customized file encoding to fix #86.
    # By default `open()` function uses `locale.getpreferredencoding(False)`
    # encoding (see https://docs.python.org/3/library/functions.html#open).
    # This code allows to change `open()` encoding by setting an environment
    # variable.
    _encoding = os.getenv(
        'RADONFILESENCODING', default_encoding
    )

    _open_function = open

    @contextmanager
    def _open(path):
        '''Mock of the built-in `open()` function. If `path` is `-` then
        `sys.stdin` is returned.
        '''
        if path == '-':
            yield sys.stdin
        else:
            with _open_function(path, encoding=_encoding) as f:
                yield f


def _is_python_file(filename):
    '''Check if a file is a Python source file.'''
    if filename == '-' or filename.endswith('.py'):
        return True
    try:
        with open(filename) as fobj:
            first_line = fobj.readline()
            if first_line.startswith('#!') and 'python' in first_line:
                return True
    except Exception:
        return False
    return False


def iter_filenames(paths, exclude=None, ignore=None):
    '''A generator that yields all sub-paths of the ones specified in
    `paths`. Optional `exclude` filters can be passed as a comma-separated
    string of regexes, while `ignore` filters are a comma-separated list of
    directory names to ignore. Ignore patterns are can be plain names or glob
    patterns. If paths contains only a single hyphen, stdin is implied,
    returned as is.
    '''
    if set(paths) == set(('-',)):
        yield '-'
        return
    exclude = exclude.split(',') if exclude else []
    ignore = f'.*,{ignore}'.split(',') if ignore else ['.*']
    for path in paths:
        if (
            os.path.isfile(path)
            and _is_python_file(path)
            and (
                not exclude
                or not any(fnmatch.fnmatch(path, p) for p in exclude)
            )
        ):
            yield path
            continue
        # Keep the outer generator from delegating its protocol methods.
        for filename in explore_directories(path, exclude, ignore):  # noqa: UP028
            yield filename


def explore_directories(start, exclude, ignore):
    '''Explore files and directories under `start`. `explore` and `ignore`
    arguments are the same as in :func:`iter_filenames`.
    '''
    for root, dirs, files in os.walk(start):
        dirs[:] = list(filter_out(dirs, ignore))
        fullpaths = (os.path.normpath(os.path.join(root, p)) for p in files)
        for filename in filter_out(fullpaths, exclude):
            if not os.path.basename(filename).startswith(
                '.'
            ) and _is_python_file(filename):
                yield filename


def filter_out(strings, patterns):
    '''Filter out any string that matches any of the specified patterns.'''
    for s in strings:
        if all(not fnmatch.fnmatch(s, p) for p in patterns):
            yield s


def cc_to_dict(obj):
    '''Convert an object holding CC results into a dictionary. This is meant
    for JSON dumping.'''

    def get_type(obj):
        '''The object can be of type *method*, *function* or *class*.'''
        if isinstance(obj, Function):
            return 'method' if obj.is_method else 'function'
        return 'class'

    result = {
        'type': get_type(obj),
        'rank': cc_rank(obj.complexity),
    }
    attrs = set(Function._fields) - set(('is_method', 'closures'))
    for a in attrs:
        v = getattr(obj, a, None)
        if v is not None:
            result[a] = v
    for key in ('methods', 'closures'):
        if hasattr(obj, key):
            result[key] = list(map(cc_to_dict, getattr(obj, key)))
    return result


def raw_to_dict(obj):
    '''Convert an object holding raw analysis results into a dictionary. This
    is meant for JSON dumping.'''
    result = {}
    for a in obj._fields:
        v = getattr(obj, a, None)
        if v is not None:
            result[a] = v
    return result


def dict_to_xml(results):
    '''Convert a dictionary holding CC analysis result into a string containing
    xml.'''
    ccm = et.Element('ccm')
    for filename, blocks in results.items():
        for block in blocks:
            metric = et.SubElement(ccm, 'metric')
            et.SubElement(metric, 'complexity').text = str(block['complexity'])

            unit = et.SubElement(metric, 'unit')
            name = block['name']
            if 'classname' in block:
                name = '{}.{}'.format(block['classname'], block['name'])
            unit.text = name

            et.SubElement(metric, 'classification').text = block['rank']
            et.SubElement(metric, 'file').text = filename
            et.SubElement(metric, 'startLineNumber').text = str(
                block['lineno']
            )
            et.SubElement(metric, 'endLineNumber').text = str(block['endline'])
    return et.tostring(ccm).decode('utf-8')


def dict_to_md(results):
    md_string = '''
| Filename | Name | Type | Start:End Line | Complexity | Classification |
| -------- | ---- | ---- | -------------- | ---------- | -------------- |
'''
    type_letter_map = {'class': 'C',
                       'method': 'M',
                       'function': 'F'}
    for filename, blocks in results.items():
        for block in blocks:
            raw_classname = block.get("classname")
            raw_name = block.get("name")
            name = f"{raw_classname}.{raw_name}" if raw_classname else block["name"]
            type = type_letter_map[block["type"]]
            md_string += "| {} | {} | {} | {}:{} | {} | {} |\n".format(
                filename,
                name,
                type,
                block["lineno"],
                block["endline"],
                block["complexity"],
                block["rank"])
    return md_string


def cc_to_terminal(results, show_complexity, min, max, total_average):
    '''Transform Cyclomatic Complexity results into a 3-elements tuple:

        ``(res, total_cc, counted)``

    `res` is a list holding strings that are specifically formatted to be
    printed to a terminal.
    `total_cc` is a number representing the total analyzed cyclomatic
    complexity.
    `counted` holds the number of the analyzed blocks.

    If *show_complexity* is `True`, then the complexity of a block will be
    shown in the terminal line alongside its rank.
    *min* and *max* are used to control which blocks are shown in the resulting
    list. A block is formatted only if its rank is `min <= rank <= max`.
    If *total_average* is `True`, the `total_cc` and `counted` count every
    block, regardless of the fact that they are formatted in `res` or not.
    '''
    res = []
    counted = 0
    total_cc = 0.0
    for line in results:
        ranked = cc_rank(line.complexity)
        if min <= ranked <= max:
            total_cc += line.complexity
            counted += 1
            res.append(_format_line(line, ranked, show_complexity))
        elif total_average:
            total_cc += line.complexity
            counted += 1
    return res, total_cc, counted


def _format_line(block, ranked, show_complexity=False):
    '''Format a single block as a line.

    *ranked* is the rank given by the `~radon.complexity.rank` function. If
    *show_complexity* is True, then the complexity score is added alongside.
    '''
    letter_colored = LETTERS_COLORS[block.letter] + block.letter
    rank_colored = RANKS_COLORS[ranked] + ranked
    compl = '' if not show_complexity else f' ({block.complexity})'
    return TEMPLATE.format(
        BRIGHT,
        letter_colored,
        block.lineno,
        block.col_offset,
        block.fullname,
        rank_colored,
        compl,
        reset=RESET,
    )
