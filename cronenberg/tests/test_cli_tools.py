import os
import platform
import sys

import pytest

import cronenberg.cli.tools as tools
from cronenberg.raw import Module
from cronenberg.visitors import Class, Function


def fake_isfile(filename):
    if filename == 'file.py':
        return True
    return False


def fake_walk(start):
    dirs = ['tests', 'sub', '.hid']
    contents = {
        'tests': ['test_amod.py', 'run.py', '.hid.py'],
        'sub': ['amod.py', 'bmod.py'],
    }
    yield '.', dirs, ['tox.ini', 'amod.py', 'test_all.py', 'fake.yp', 'noext']
    for d in dirs:
        yield f'./{d}', [], contents[d]


def fake_is_python_file(filename):
    return filename.endswith('.py')


class ProtocolProbe:
    def __init__(self, values):
        self.values = iter(values)
        self.send_calls = 0
        self.throw_calls = 0
        self.close_calls = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.values)
        except StopIteration:
            raise StopIteration('delegated return') from None

    def send(self, value):
        self.send_calls += 1
        raise AssertionError(f'unexpected send: {value!r}')

    def throw(self, *args):
        self.throw_calls += 1
        raise AssertionError(f'unexpected throw: {args!r}')

    def close(self):
        self.close_calls += 1


def assert_pequal(a, b):
    a, b = [list(map(os.path.normpath, p)) for p in (a, b)]
    assert a == b


def test_open(mocker):
    with tools._open('-') as fobj:
        assert fobj is sys.stdin

    try:
        with tools._open(__file__) as fobj:
            assert True
    except TypeError:  # issue 101
        assert False, 'tools._open raised TypeError'

    m = mocker.mock_open()

    if platform.python_implementation() == 'PyPy':
        mocker.patch('cronenberg.cli.tools.open', m, create=True)
        tools._open('randomfile.py').__enter__()
        m.assert_called_with('randomfile.py')
    else:
        mocker.patch('cronenberg.cli.tools._open_function', m, create=True)
        tools._open('randomfile.py').__enter__()
        default_encoding = 'utf-8'
        except_encoding = os.getenv(
            'RADONFILESENCODING', default_encoding
        )
        m.assert_called_with('randomfile.py', encoding=except_encoding)


@pytest.fixture
def iter_files():
    return lambda *a, **kw: list(tools.iter_filenames(*a, **kw))


def test_iter_files_stdin(iter_files):
    assert iter_files(['-']) == ['-']


def test_python_file_discovery_rejects_removed_file_type(tmp_path):
    python_file = tmp_path / 'module.py'
    python_file.write_text('value = 1\n')
    unsupported_file = tmp_path / ('example.' + ''.join(('ip', 'ynb')))
    unsupported_file.write_text('{}\n')

    assert tools._is_python_file(str(python_file))
    assert not tools._is_python_file(str(unsupported_file))
    assert list(tools.iter_filenames([str(tmp_path)])) == [str(python_file)]


def test_iter_files_does_not_delegate_send_or_return(mocker):
    probe = ProtocolProbe(['first.py', 'second.py'])
    mocker.patch.object(tools, 'explore_directories', return_value=probe)
    iterator = tools.iter_filenames(['directory'])

    assert next(iterator) == 'first.py'
    assert iterator.send('ignored') == 'second.py'
    assert probe.send_calls == 0
    with pytest.raises(StopIteration) as completed:
        next(iterator)
    assert completed.value.value is None


def test_iter_files_does_not_delegate_throw(mocker):
    probe = ProtocolProbe(['first.py'])
    mocker.patch.object(tools, 'explore_directories', return_value=probe)
    iterator = tools.iter_filenames(['directory'])

    assert next(iterator) == 'first.py'
    with pytest.raises(RuntimeError, match='boom'):
        iterator.throw(RuntimeError('boom'))
    assert probe.throw_calls == 0


def test_iter_files_does_not_delegate_close(mocker):
    probe = ProtocolProbe(['first.py'])
    mocker.patch.object(tools, 'explore_directories', return_value=probe)
    iterator = tools.iter_filenames(['directory'])

    assert next(iterator) == 'first.py'
    iterator.close()
    assert probe.close_calls == 0
    with pytest.raises(StopIteration):
        next(iterator)


def test_iter_files(mocker, iter_files):
    os_mod = mocker.patch('cronenberg.cli.tools.os')
    os_path_mod = mocker.patch('cronenberg.cli.tools.os.path')
    os_path_mod.normpath = os.path.normpath
    os_path_mod.basename = os.path.basename
    os_path_mod.join = os.path.join

    os_path_mod.isfile.side_effect = fake_isfile
    _orig_walk = os_mod.walk
    os_mod.walk = fake_walk
    _orig_is_python_file = tools._is_python_file
    tools._is_python_file = fake_is_python_file

    assert_pequal(
        iter_files(['file.py', 'random/path']),
        [
            'file.py',
            'amod.py',
            'test_all.py',
            'tests/test_amod.py',
            'tests/run.py',
            'sub/amod.py',
            'sub/bmod.py',
        ],
    )

    assert_pequal(
        iter_files(['file.py', 'random/path'], 'test_*'),
        [
            'file.py',
            'amod.py',
            'tests/test_amod.py',
            'tests/run.py',
            'sub/amod.py',
            'sub/bmod.py',
        ],
    )

    assert_pequal(
        iter_files(['file.py', 'random/path'], '*test_*'),
        ['file.py', 'amod.py', 'tests/run.py', 'sub/amod.py', 'sub/bmod.py'],
    )

    assert_pequal(
        iter_files(['file.py', 'random/path'], '*/test_*,amod*'),
        [
            'file.py',
            'test_all.py',
            'tests/run.py',
            'sub/amod.py',
            'sub/bmod.py',
        ],
    )

    assert_pequal(
        iter_files(['file.py', 'random/path'], None, 'tests'),
        ['file.py', 'amod.py', 'test_all.py', 'sub/amod.py', 'sub/bmod.py'],
    )

    assert_pequal(
        iter_files(['file.py', 'random/path'], None, 'tests,sub'),
        ['file.py', 'amod.py', 'test_all.py'],
    )
    tools._is_python_file = _orig_is_python_file
    os_mod.walk = _orig_walk


CC_RESULTS_CASES = [
    (
        Function('name', 12, 0, 16, False, None, [], 6),
        {
            'type': 'function',
            'name': 'name',
            'lineno': 12,
            'col_offset': 0,
            'endline': 16,
            'closures': [],
            'complexity': 6,
            'rank': 'B',
        },
    ),
    (
        Class(
            'Classname',
            17,
            0,
            29,
            [Function('name', 19, 4, 26, True, 'Classname', [], 7)],
            [],
            7,
        ),
        {
            'type': 'class',
            'name': 'Classname',
            'lineno': 17,
            'col_offset': 0,
            'endline': 29,
            'complexity': 7,
            'rank': 'B',
            'methods': [
                {
                    'type': 'method',
                    'lineno': 19,
                    'col_offset': 4,
                    'endline': 26,
                    'closures': [],
                    'complexity': 7,
                    'rank': 'B',
                    'classname': 'Classname',
                    'name': 'name',
                }
            ],
        },
    ),
    (
        Function(
            'name',
            12,
            0,
            16,
            False,
            None,
            [Function('aux', 13, 4, 17, False, None, [], 4)],
            10,
        ),
        {
            'type': 'function',
            'name': 'name',
            'lineno': 12,
            'col_offset': 0,
            'endline': 16,
            'complexity': 10,
            'rank': 'B',
            'closures': [
                {
                    'name': 'aux',
                    'lineno': 13,
                    'col_offset': 4,
                    'endline': 17,
                    'closures': [],
                    'complexity': 4,
                    'rank': 'A',
                    'type': 'function',
                }
            ],
        },
    ),
]


@pytest.mark.parametrize('blocks,dict_result', CC_RESULTS_CASES)
def test_cc_to_dict(blocks, dict_result):
    assert tools.cc_to_dict(blocks) == dict_result


CC_TO_XML_CASE = [
    {
        'closures': [],
        'endline': 16,
        'complexity': 6,
        'lineno': 12,
        'is_method': False,
        'name': 'name',
        'col_offset': 0,
        'rank': 'B',
    },
    {
        'complexity': 8,
        'endline': 29,
        'rank': 'B',
        'lineno': 17,
        'name': 'Classname',
        'col_offset': 0,
    },
    {
        'classname': 'Classname',
        'closures': [],
        'endline': 26,
        'complexity': 7,
        'lineno': 19,
        'is_method': True,
        'name': 'name',
        'col_offset': 4,
        'rank': 'B',
    },
    {
        'closures': [],
        'endline': 17,
        'complexity': 4,
        'lineno': 13,
        'is_method': False,
        'name': 'aux',
        'col_offset': 4,
        'rank': 'A',
    },
    {
        'endline': 16,
        'complexity': 10,
        'lineno': 12,
        'is_method': False,
        'name': 'name',
        'col_offset': 0,
        'rank': 'B',
    },
]


def test_raw_to_dict():
    assert tools.raw_to_dict(Module(103, 123, 98, 8, 19, 5, 3)) == {
        'loc': 103,
        'lloc': 123,
        'sloc': 98,
        'comments': 8,
        'multi': 19,
        'blank': 5,
        'single_comments': 3,
    }


def test_cc_to_xml():
    assert (
        tools.dict_to_xml({'filename': CC_TO_XML_CASE})
        == '''<ccm>
              <metric>
                <complexity>6</complexity>
                <unit>name</unit>
                <classification>B</classification>
                <file>filename</file>
                <startLineNumber>12</startLineNumber>
                <endLineNumber>16</endLineNumber>
              </metric>
              <metric>
                <complexity>8</complexity>
                <unit>Classname</unit>
                <classification>B</classification>
                <file>filename</file>
                <startLineNumber>17</startLineNumber>
                <endLineNumber>29</endLineNumber>
              </metric>
              <metric>
                <complexity>7</complexity>
                <unit>Classname.name</unit>
                <classification>B</classification>
                <file>filename</file>
                <startLineNumber>19</startLineNumber>
                <endLineNumber>26</endLineNumber>
              </metric>
              <metric>
                <complexity>4</complexity>
                <unit>aux</unit>
                <classification>A</classification>
                <file>filename</file>
                <startLineNumber>13</startLineNumber>
                <endLineNumber>17</endLineNumber>
              </metric>
              <metric>
                <complexity>10</complexity>
                <unit>name</unit>
                <classification>B</classification>
                <file>filename</file>
                <startLineNumber>12</startLineNumber>
                <endLineNumber>16</endLineNumber>
              </metric>
            </ccm>'''.replace(
            '\n', ''
        ).replace(
            ' ', ''
        )
    )


CC_TO_MD_RESULTS = [
    {"type": "method", "rank": "A", "lineno": 110, "classname": "Classname", "endline": 117,
     "complexity": 2, "name": "flush", "col_offset": 4},
    {"type": "class", "rank": "B", "lineno": 73, "endline": 124, "complexity": 4, "name": "Classname",
     "col_offset": 0},
    {'type': 'function', 'rank': 'C', 'lineno': 62, 'endline': 69, 'complexity': 10, 'name': 'decrement',
     'col_offset': 0}
]


def test_cc_to_md():
    md = tools.dict_to_md({'filename': CC_TO_MD_RESULTS})
    _md = '''
| Filename | Name | Type | Start:End Line | Complexity | Classification |
| -------- | ---- | ---- | -------------- | ---------- | -------------- |
| filename | Classname.flush | M | 110:117 | 2 | A |
| filename | Classname | C | 73:124 | 4 | B |
| filename | decrement | F | 62:69 | 10 | C |
'''
    assert md == _md


CC_TO_TERMINAL_CASES = [
    Class(
        name='Classname',
        lineno=17,
        col_offset=0,
        endline=29,
        methods=[
            Function(
                name='meth',
                lineno=19,
                col_offset=4,
                endline=26,
                is_method=True,
                classname='Classname',
                closures=[],
                complexity=4,
            )
        ],
        inner_classes=[],
        real_complexity=4,
    ),
    Function(
        name='meth',
        lineno=19,
        col_offset=4,
        endline=26,
        is_method=True,
        classname='Classname',
        closures=[],
        complexity=7,
    ),
    Function(
        name='f1',
        lineno=12,
        col_offset=0,
        endline=16,
        is_method=False,
        classname=None,
        closures=[],
        complexity=14,
    ),
    Function(
        name='f2',
        lineno=12,
        col_offset=0,
        endline=16,
        is_method=False,
        classname=None,
        closures=[],
        complexity=22,
    ),
    Function(
        name='f3',
        lineno=12,
        col_offset=0,
        endline=16,
        is_method=False,
        classname=None,
        closures=[],
        complexity=32,
    ),
    Function(
        name='f4',
        lineno=12,
        col_offset=0,
        endline=16,
        is_method=False,
        classname=None,
        closures=[],
        complexity=41,
    ),
]


def test_cc_to_terminal():
    # do the patching
    tools.LETTERS_COLORS = dict((letter, f'<!{letter}!>') for letter in 'FMC')
    tools.RANKS_COLORS = dict((r, f'<|{r}|>') for r in 'ABCDEF')
    tools.BRIGHT = '@'
    tools.RESET = '__R__'

    results = CC_TO_TERMINAL_CASES
    res = [
        '@<!C!>C __R__17:0 Classname - <|A|>A (4)__R__',
        '@<!M!>M __R__19:4 Classname.meth - <|B|>B (7)__R__',
        '@<!F!>F __R__12:0 f1 - <|C|>C (14)__R__',
        '@<!F!>F __R__12:0 f2 - <|D|>D (22)__R__',
        '@<!F!>F __R__12:0 f3 - <|E|>E (32)__R__',
        '@<!F!>F __R__12:0 f4 - <|F|>F (41)__R__',
    ]
    res_noshow = ['{}__R__'.format(r[: r.index('(') - 1]) for r in res]

    assert tools.cc_to_terminal(results, False, 'A', 'F', False) == (
        res_noshow,
        120,
        6,
    )
    assert tools.cc_to_terminal(results, True, 'A', 'F', False) == (
        res,
        120,
        6,
    )
    assert tools.cc_to_terminal(results, True, 'A', 'D', False) == (
        res[:-2],
        47,
        4,
    )
    assert tools.cc_to_terminal(results, False, 'A', 'D', False) == (
        res_noshow[:-2],
        47,
        4,
    )
    assert tools.cc_to_terminal(results, True, 'C', 'F', False) == (
        res[2:],
        109,
        4,
    )
    assert tools.cc_to_terminal(results, True, 'B', 'E', False) == (
        res[1:-1],
        75,
        4,
    )
    assert tools.cc_to_terminal(results, True, 'B', 'F', True) == (
        res[1:],
        120,
        6,
    )
