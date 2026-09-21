import operator

import pytest

from radon.complexity import (
    ALPHA,
    LINES,
    SCORE,
    add_inner_blocks,
    average_complexity,
    cc_rank,
    cc_visit,
    sorted_results,
)
from radon.visitors import Class, Function

from .test_complexity_visitor import GENERAL_CASES, dedent


def get_index(seq):
    return lambda index: seq[index]


def _compute_cc_rank(score):
    # This is really ugly
    # Luckily the rank function in radon.complexity is not like this!
    if score < 0:
        rank = ValueError
    elif 0 <= score <= 5:
        rank = 'A'
    elif 6 <= score <= 10:
        rank = 'B'
    elif 11 <= score <= 20:
        rank = 'C'
    elif 21 <= score <= 30:
        rank = 'D'
    elif 31 <= score <= 40:
        rank = 'E'
    else:
        rank = 'F'
    return rank


RANK_CASES = [(score, _compute_cc_rank(score)) for score in range(-1, 100)]


@pytest.mark.parametrize('score,expected_rank', RANK_CASES)
def test_rank(score, expected_rank):
    if hasattr(expected_rank, '__call__') and isinstance(
        expected_rank(), Exception
    ):
        with pytest.raises(expected_rank):
            cc_rank(score)
    else:
        assert cc_rank(score) == expected_rank


def fun(complexity):
    return Function('randomname', 1, 4, 23, False, None, [], complexity)


def cls(complexity):
    return Class('randomname_', 3, 21, 18, [], [], complexity)

# This works with both the next two tests
SIMPLE_BLOCKS = [
    ([], [], 0.0),
    ([fun(12), fun(14), fun(1)], [1, 0, 2], 9.0),
    ([fun(4), cls(5), fun(2), cls(21)], [3, 1, 0, 2], 8.0),
]


def test_public_ordering_callable_identity():
    block = fun(4)

    assert sorted_results.__defaults__[0] is SCORE
    assert [ordering.__name__ for ordering in (SCORE, LINES, ALPHA)] == [
        '<lambda>',
        '<lambda>',
        '<lambda>',
    ]
    assert all('<lambda>' in repr(ordering) for ordering in (SCORE, LINES, ALPHA))
    assert (SCORE(block), LINES(block), ALPHA(block)) == (-4, 1, 'randomname')


@pytest.mark.parametrize('blocks,indices,_', SIMPLE_BLOCKS)
def test_sorted_results(blocks, indices, _):
    expected_result = list(map(get_index(blocks), indices))
    assert sorted_results(blocks) == expected_result


@pytest.mark.parametrize('blocks,_,expected_average', SIMPLE_BLOCKS)
def test_average_complexity(blocks, _, expected_average):
    assert average_complexity(blocks) == expected_average


CC_VISIT_CASES = [
    (GENERAL_CASES[0][0], 1, 1, 'f.inner'),
    (GENERAL_CASES[1][0], 3, 1, 'f.inner'),
    (
        '''
    class joe1:
        i = 1
        def doit1(self):
            pass
        class joe2:
            ii = 2
            def doit2(self):
                pass
            class joe3:
                iii = 3
                def doit3(self):
                    pass
     ''',
        2,
        4,
        'joe1.joe2.joe3',
    ),
]


@pytest.mark.parametrize('code,number_of_blocks,diff,lookfor', CC_VISIT_CASES)
def test_cc_visit(code, number_of_blocks, diff, lookfor):
    code = dedent(code)

    blocks = cc_visit(code)
    assert isinstance(blocks, list)
    assert len(blocks) == number_of_blocks

    with_inner_blocks = add_inner_blocks(blocks)
    names = set(map(operator.attrgetter('name'), with_inner_blocks))
    assert len(with_inner_blocks) - len(blocks) == diff
    assert lookfor in names
