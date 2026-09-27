import operator

import pytest

from cronenberg.cli import Config
from cronenberg.cli.harvest import CCHarvester
from cronenberg.complexity import (
    ALPHA,
    LINES,
    SCORE,
    add_inner_blocks,
    average_complexity,
    cc_rank,
    cc_visit,
    sorted_results,
)
from cronenberg.visitors import Class, ComplexityVisitor, Function

from .test_complexity_visitor import GENERAL_CASES, dedent


def get_index(seq):
    return lambda index: seq[index]


def _compute_cc_rank(score):
    # This is really ugly
    # Luckily the rank function in cronenberg.complexity is not like this!
    if score < 0:
        rank = ValueError
    elif 0 <= score <= 5:
        rank = "A"
    elif 6 <= score <= 10:
        rank = "B"
    elif 11 <= score <= 20:
        rank = "C"
    elif 21 <= score <= 30:
        rank = "D"
    elif 31 <= score <= 40:
        rank = "E"
    else:
        rank = "F"
    return rank


RANK_CASES = [(score, _compute_cc_rank(score)) for score in range(-1, 100)]


@pytest.mark.parametrize("score,expected_rank", RANK_CASES)
def test_rank(score, expected_rank):
    if hasattr(expected_rank, "__call__") and isinstance(expected_rank(), Exception):
        with pytest.raises(expected_rank):
            cc_rank(score)
    else:
        assert cc_rank(score) == expected_rank


def fun(complexity):
    return Function("randomname", 1, 4, 23, False, None, [], complexity)


def cls(complexity):
    return Class("randomname_", 3, 21, 18, [], [], complexity)


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
        "<lambda>",
        "<lambda>",
        "<lambda>",
    ]
    assert all("<lambda>" in repr(ordering) for ordering in (SCORE, LINES, ALPHA))
    assert (SCORE(block), LINES(block), ALPHA(block)) == (-4, 1, "randomname")


@pytest.mark.parametrize("blocks,indices,_", SIMPLE_BLOCKS)
def test_sorted_results(blocks, indices, _):
    expected_result = list(map(get_index(blocks), indices))
    assert sorted_results(blocks) == expected_result


@pytest.mark.parametrize("blocks,_,expected_average", SIMPLE_BLOCKS)
def test_average_complexity(blocks, _, expected_average):
    assert average_complexity(blocks) == expected_average


CC_VISIT_CASES = [
    (GENERAL_CASES[0][0], 1, 1, "f.inner"),
    (GENERAL_CASES[1][0], 3, 1, "f.inner"),
    (
        """
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
     """,
        2,
        4,
        "joe1.joe2.joe3",
    ),
]


@pytest.mark.parametrize("code,number_of_blocks,diff,lookfor", CC_VISIT_CASES)
def test_cc_visit(code, number_of_blocks, diff, lookfor):
    code = dedent(code)

    blocks = cc_visit(code)
    assert isinstance(blocks, list)
    assert len(blocks) == number_of_blocks

    with_inner_blocks = add_inner_blocks(blocks)
    names = set(map(operator.attrgetter("name"), with_inner_blocks))
    assert len(with_inner_blocks) - len(blocks) == diff
    assert lookfor in names


# The Radon issue 215 sample, unchanged.
RADON_215_SAMPLE = """\
class student2:
    def nott(self):
        if True and False:
            return
        elif True:
            return
        else:
            return
        return self
    class classmate:
        def example(self):
            return 0
    @staticmethod
    def staticMethod():
        return None
"""

# The same class with the nested classmate block removed.
RADON_215_SAMPLE_WITHOUT_NESTED_CLASS = """\
class student2:
    def nott(self):
        if True and False:
            return
        elif True:
            return
        else:
            return
        return self
    @staticmethod
    def staticMethod():
        return None
"""


def _public_cc_blocks(path, *, show_closures):
    """Return the ``CCHarvester.as_dict`` blocks for one file."""
    config = Config(
        min="A",
        max="F",
        exclude=None,
        ignore=None,
        show_complexity=False,
        average=False,
        total_average=False,
        order=SCORE,
        no_assert=False,
        show_closures=show_closures,
    )
    filename = str(path)
    return CCHarvester([filename], config).as_dict()[filename]


def _cc_identity(block):
    return (block["type"], block["name"], block.get("classname"), block["complexity"])


def test_default_cc_omits_nested_class(tmp_path):
    """Record that default cc drops a nested class and ignores its code.

    This records the defect and is not the desired end state. The sample is
    the nested ``student2`` / ``classmate`` class from Radon issue 215.
    """
    visitor = ComplexityVisitor.from_code(RADON_215_SAMPLE)
    student = visitor.classes[0]
    classmate = student.inner_classes[0]
    bare = ComplexityVisitor.from_code(RADON_215_SAMPLE_WITHOUT_NESTED_CLASS).classes[0]

    assert [(block.letter, block.fullname, block.complexity) for block in visitor.blocks] == [
        ("C", "student2", 4),
        ("M", "student2.nott", 4),
        ("M", "student2.staticMethod", 1),
    ]
    assert classmate.name == "classmate"
    assert (classmate.complexity, classmate.real_complexity) == (2, 2)
    assert [(method.fullname, method.complexity) for method in classmate.methods] == [
        ("classmate.example", 1),
    ]
    reported = {block.fullname for block in visitor.blocks}
    assert "classmate" not in reported
    assert "classmate.example" not in reported

    assert (student.complexity, student.real_complexity) == (4, 6)
    assert (bare.complexity, bare.real_complexity) == (student.complexity, student.real_complexity)
    assert [(method.name, method.complexity) for method in bare.methods] == [
        (method.name, method.complexity) for method in student.methods
    ]

    sample_path = tmp_path / "student2.py"
    sample_path.write_text(RADON_215_SAMPLE, encoding="utf-8")
    default_blocks = _public_cc_blocks(sample_path, show_closures=False)
    assert [_cc_identity(block) for block in default_blocks] == [
        ("class", "student2", None, 4),
        ("method", "nott", "student2", 4),
        ("method", "staticMethod", "student2", 1),
    ]
    assert [(method["name"], method["classname"], method["complexity"]) for method in default_blocks[0]["methods"]] == [
        ("nott", "student2", 4),
        ("staticMethod", "student2", 1),
    ]

    closure_blocks = _public_cc_blocks(sample_path, show_closures=True)
    assert [_cc_identity(block) for block in closure_blocks] == [
        ("method", "nott", "student2", 4),
        ("class", "student2", None, 4),
        ("class", "student2.classmate", None, 2),
        ("method", "staticMethod", "student2", 1),
        ("method", "example", "student2.classmate", 1),
    ]
    nested = closure_blocks[2]
    assert [(method["name"], method["classname"], method["complexity"]) for method in nested["methods"]] == [
        ("example", "classmate", 1),
    ]
