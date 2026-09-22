"""Tests that ``--json`` dumps one stable public dictionary."""

import json
import os
import subprocess
import textwrap

import cronenberg.cli.harvest as harvest
import cronenberg.complexity as cc_mod
from cronenberg.cli import Config

Z_SOURCE = textwrap.dedent(
    """\
    def low():
        return 1

    def high(value):
        if value:
            return 1
        return 0
    """
)
A_SOURCE = "def other():\n    return 0\n"


def _paths(tmp_path):
    z_path = tmp_path / "z.py"
    a_path = tmp_path / "a.py"
    z_path.write_text(Z_SOURCE)
    a_path.write_text(A_SOURCE)
    return [str(z_path), str(a_path)]


def _cc_harvester(paths):
    config = Config(
        order=cc_mod.SCORE,
        no_assert=False,
        min="A",
        max="F",
        show_complexity=False,
        show_closures=False,
        average=False,
        total_average=False,
        exclude=None,
        ignore=None,
    )
    return harvest.CCHarvester(paths, config)


def _harvesters(paths):
    return (
        _cc_harvester(paths),
        harvest.RawHarvester(paths, Config(exclude=None, ignore=None, summary=False)),
        harvest.MIHarvester(
            paths,
            Config(
                min="A",
                max="C",
                multi=True,
                show=False,
                sort=False,
                exclude=None,
                ignore=None,
            ),
        ),
        harvest.HCHarvester(paths, Config(exclude=None, ignore=None, by_function=False)),
    )


def test_as_dict_keeps_values_and_list_order(tmp_path):
    paths = _paths(tmp_path)
    cc, raw, mi, hal = _harvesters(paths)

    cc_payload = cc.as_dict()
    assert list(cc_payload) == paths
    assert [block["name"] for block in cc_payload[paths[0]]] == ["high", "low"]
    assert [block["complexity"] for block in cc_payload[paths[0]]] == [2, 1]
    assert [block["name"] for block in cc_payload[paths[1]]] == ["other"]
    assert cc_payload[paths[1]][0]["complexity"] == 1

    raw_payload = raw.as_dict()
    assert list(raw_payload) == paths
    assert raw_payload[paths[0]]["loc"] == 7
    assert raw_payload[paths[0]]["lloc"] == 6
    assert raw_payload[paths[0]]["sloc"] == 6
    assert raw_payload[paths[0]]["blank"] == 1
    assert raw_payload[paths[1]]["loc"] == 2
    assert raw_payload[paths[1]]["blank"] == 0

    mi_payload = mi.as_dict()
    assert list(mi_payload) == paths
    assert mi_payload[paths[0]] == {"mi": 100.0, "rank": "A"}
    assert mi_payload[paths[1]] == {"mi": 100.0, "rank": "A"}

    hal_payload = hal.as_dict()
    assert list(hal_payload) == paths
    assert list(hal_payload[paths[0]]["functions"]) == ["low", "high"]
    assert set(hal_payload[paths[0]]["total"]) == {
        "h1",
        "h2",
        "N1",
        "N2",
        "vocabulary",
        "length",
        "calculated_length",
        "volume",
        "difficulty",
        "effort",
        "time",
        "bugs",
    }

    for harvester, payload in (
        (cc, cc_payload),
        (raw, raw_payload),
        (mi, mi_payload),
        (hal, hal_payload),
    ):
        text = harvester.as_json()
        assert text == json.dumps(payload, sort_keys=True)
        assert json.loads(text) == payload
        assert text == harvester.as_json()


def test_cli_json_bytes_ignore_pythonhashseed(tmp_path):
    paths = _paths(tmp_path)
    commands = {
        "cc": ["cc", *paths, "-j", "-s"],
        "raw": ["raw", *paths, "-j"],
        "mi": ["mi", *paths, "-j", "-s"],
        "hal": ["hal", *paths, "-j"],
    }
    expected = {name: harvester.as_dict() for name, harvester in zip(commands, _harvesters(paths), strict=True)}

    for name, command in commands.items():
        outputs = []
        for seed in ("1", "2"):
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = seed
            result = subprocess.run(
                ["cronenberg", *command],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            assert result.returncode == 0
            outputs.append(result.stdout)
        assert outputs[0] == outputs[1]
        parsed = json.loads(outputs[0])
        assert parsed == expected[name]
        assert list(parsed) == sorted(paths)
        if name == "cc":
            assert [block["name"] for block in parsed[paths[0]]] == ["high", "low"]
            assert [block["complexity"] for block in parsed[paths[0]]] == [2, 1]


def test_cli_cc_terminal_text_stays(tmp_path):
    paths = _paths(tmp_path)
    result = subprocess.run(
        ["cronenberg", "cc", *paths, "-s"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == (
        f"{paths[0]}\n"
        "    F 4:0 high - A (2)\n"
        "    F 1:0 low - A (1)\n"
        f"{paths[1]}\n"
        "    F 1:0 other - A (1)\n"
    )
