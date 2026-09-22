try:
    import collections.abc as collections_abc
except ImportError:
    import collections as collections_abc

import io
import json

import pytest
from rich.console import Console

import cronenberg.cli.harvest as harvest
import cronenberg.complexity as cc_mod
from cronenberg.cli import Config
from cronenberg.cli.theme import TOKYO_NIGHT, render_cc, render_mi, render_raw

BASE_CONFIG = Config(
    exclude=r"test_[^.]+\.py",
    ignore="tests,docs",
)

CC_CONFIG = Config(
    order=getattr(cc_mod, "SCORE"),
    no_assert=False,
    min="A",
    max="F",
    show_complexity=False,
    show_closures=False,
    average=True,
    total_average=False,
    **BASE_CONFIG.config_values,
)

RAW_CONFIG = Config(
    summary=True,
)

MI_CONFIG = Config(
    multi=True,
    min="B",
    max="C",
    show=True,
    sort=False,
)


def fake_gobble(fobj):
    return 42


def fake_gobble_raising(fobj):
    raise TypeError("mystr")


def fake_run():
    for i in range(3):
        yield {f"file-{i}": i**2}


@pytest.fixture
def base_config():
    return Config(**BASE_CONFIG.config_values.copy())


@pytest.fixture
def cc_config():
    return Config(**CC_CONFIG.config_values.copy())


@pytest.fixture
def raw_config():
    return Config(**RAW_CONFIG.config_values.copy())


@pytest.fixture
def mi_config():
    return Config(**MI_CONFIG.config_values.copy())


def test_base_iter_filenames(base_config, mocker):
    iter_mock = mocker.patch("cronenberg.cli.harvest.iter_filenames")
    h = harvest.Harvester([], base_config)
    h._iter_filenames()

    iter_mock.assert_called_with([], base_config.exclude, base_config.ignore)


def test_base_gobble_not_implemented(base_config):
    h = harvest.Harvester([], base_config)
    with pytest.raises(NotImplementedError):
        h.gobble(None)


def test_base_as_xml_not_implemented(base_config):
    h = harvest.Harvester([], base_config)
    with pytest.raises(NotImplementedError):
        h.as_xml()


def test_base_as_md_not_implemented(base_config):
    h = harvest.Harvester([], base_config)
    with pytest.raises(NotImplementedError):
        h.as_md()


def _rich_text(render, payload):
    console = Console(
        theme=TOKYO_NIGHT,
        file=io.StringIO(),
        force_terminal=True,
        width=80,
        highlight=False,
        color_system="truecolor",
        record=True,
    )
    render(payload, console)
    return console.export_text(styles=False)


def test_base_run(base_config):
    h = harvest.Harvester(["-"], base_config)
    h.gobble = fake_gobble
    assert isinstance(h.run(), collections_abc.Iterator)
    assert list(h.run()) == [("-", 42)]
    h.gobble = fake_gobble_raising
    assert list(h.run()) == [("-", {"error": "mystr"})]


def test_base_results(base_config):
    h = harvest.Harvester([], base_config)
    h.run = fake_run
    results = h.results
    assert isinstance(results, collections_abc.Iterator)
    assert list(results) == [{"file-0": 0}, {"file-1": 1}, {"file-2": 4}]
    assert not isinstance(h.results, collections_abc.Iterator)
    assert isinstance(h.results, collections_abc.Iterable)
    assert isinstance(h.results, list)


def test_base_as_json(base_config):
    h = harvest.Harvester([], base_config)
    h._results = {"filename": {"complexity": 2}}
    assert h.as_json() == '{"filename": {"complexity": 2}}'


def test_cc_gobble(cc_config, mocker):
    sr_mock = mocker.patch("cronenberg.cli.harvest.sorted_results")
    cc_mock = mocker.patch("cronenberg.cli.harvest.cc_visit")
    cc_mock.return_value = []
    fobj = mocker.MagicMock()
    fobj.read.return_value = mocker.sentinel.one

    h = harvest.CCHarvester([], cc_config)
    h.config.show_closures = True
    h.gobble(fobj)

    assert fobj.read.called
    cc_mock.assert_called_with(mocker.sentinel.one, no_assert=cc_config.no_assert)
    sr_mock.assert_called_with([], order=cc_config.order)


def test_cc_to_dicts(cc_config, mocker):
    c2d_mock = mocker.patch("cronenberg.cli.harvest.cc_to_dict")
    c2d_mock.side_effect = lambda i: i
    h = harvest.CCHarvester([], cc_config)
    sample_results = [
        ("a", [{"rank": "A"}]),
        ("b", [{"rank": "B"}]),
        ("c", {"error": "An ERROR!"}),
    ]
    h._results = sample_results

    assert h._to_dicts() == dict(sample_results)
    assert c2d_mock.call_count == 2

    h.config.min = "B"
    h._results = sample_results[1:]
    assert h._to_dicts() == dict(sample_results[1:])


def test_cc_as_json_xml(cc_config, mocker):
    d2x_mock = mocker.patch("cronenberg.cli.harvest.dict_to_xml")
    to_dicts_mock = mocker.MagicMock()
    to_dicts_mock.return_value = {"a": {"rank": "A"}}

    h = harvest.CCHarvester([], cc_config)
    h._to_dicts = to_dicts_mock
    assert h.as_json() == '{"a": {"rank": "A"}}'

    h.as_xml()
    assert d2x_mock.called
    d2x_mock.assert_called_with(to_dicts_mock.return_value)
    assert to_dicts_mock.call_count == 2


def test_cc_as_md(cc_config, mocker):
    d2md_mock = mocker.patch("cronenberg.cli.harvest.dict_to_md")
    to_dicts_mock = mocker.MagicMock()
    to_dicts_mock.return_value = {"a": {"rank": "A"}}

    h = harvest.CCHarvester([], cc_config)
    h._to_dicts = to_dicts_mock
    assert h.as_md()
    assert d2md_mock.called
    d2md_mock.assert_called_with(to_dicts_mock.return_value)
    assert to_dicts_mock.call_count == 1


def test_cc_error_stays_in_json_and_rich(cc_config):
    h = harvest.CCHarvester([], cc_config)
    h._results = [("a.py", {"error": "mystr"})]

    payload = json.loads(h.as_json())
    assert payload == {"a.py": {"error": "mystr"}}
    text = _rich_text(render_cc, h.as_dict())
    assert "a.py" in text
    assert "mystr" in text


def test_raw_gobble(raw_config, mocker):
    r2d_mock = mocker.patch("cronenberg.cli.harvest.raw_to_dict")
    analyze_mock = mocker.patch("cronenberg.cli.harvest.analyze")
    fobj = mocker.MagicMock()
    fobj.read.return_value = mocker.sentinel.one
    analyze_mock.return_value = mocker.sentinel.two

    h = harvest.RawHarvester([], raw_config)
    h.gobble(fobj)

    assert fobj.read.call_count == 1
    analyze_mock.assert_called_once_with(mocker.sentinel.one)
    r2d_mock.assert_called_once_with(mocker.sentinel.two)


def test_raw_as_xml(raw_config):
    h = harvest.RawHarvester([], raw_config)
    with pytest.raises(NotImplementedError):
        h.as_xml()


def test_raw_error_and_metrics_json_and_rich(raw_config):
    h = harvest.RawHarvester([], raw_config)
    records = [
        ("a", {"error": "mystr"}),
        (
            "b",
            {
                "loc": 24,
                "lloc": 27,
                "sloc": 15,
                "comments": 3,
                "multi": 3,
                "single_comments": 3,
                "blank": 9,
            },
        ),
    ]
    h._results = records

    assert h.as_dict() == dict(records)
    assert json.loads(h.as_json())["a"] == {"error": "mystr"}
    text = _rich_text(render_raw, h.as_dict())
    assert "mystr" in text
    assert "loc" in text
    assert "24" in text


def test_mi_gobble(mi_config, mocker):
    mv_mock = mocker.patch("cronenberg.cli.harvest.mi_visit")
    fobj = mocker.MagicMock()
    fobj.read.return_value = mocker.sentinel.one
    mv_mock.return_value = 23.5

    h = harvest.MIHarvester([], mi_config)
    result = h.gobble(fobj)

    assert fobj.read.call_count == 1
    mv_mock.assert_called_once_with(mocker.sentinel.one, mi_config.multi)
    assert result == {"mi": 23.5, "rank": "A"}


def test_mi_as_json(mi_config, mocker):
    d_mock = mocker.patch("cronenberg.cli.harvest.json.dumps")
    h = harvest.MIHarvester([], mi_config)
    h.config.min = "C"
    h._results = [
        ("a", {"error": "mystr"}),
        ("b", {"mi": 25, "rank": "A"}),
        ("c", {"mi": 15, "rank": "B"}),
        ("d", {"mi": 0, "rank": "C"}),
    ]

    h.as_json()
    d_mock.assert_called_with(dict([h._results[0], h._results[-1]]), sort_keys=True)


def test_mi_as_xml(mi_config):
    h = harvest.MIHarvester([], mi_config)
    with pytest.raises(NotImplementedError):
        h.as_xml()


def test_mi_filtered_error_json_and_rich(mi_config):
    h = harvest.MIHarvester([], mi_config)
    h._results = [
        ("a", {"error": "mystr"}),
        ("b", {"mi": 25, "rank": "A"}),
        ("c", {"mi": 15, "rank": "B"}),
        ("d", {"mi": 0, "rank": "C"}),
    ]

    assert json.loads(h.as_json()) == {
        "a": {"error": "mystr"},
        "c": {"mi": 15, "rank": "B"},
        "d": {"mi": 0, "rank": "C"},
    }
    text = _rich_text(render_mi, h.as_dict())
    assert "mystr" in text
    assert "B" in text
    assert "C" in text
    assert list(h.as_dict()) == ["a", "c", "d"]
