"""Tests for cc Rich themes and terminal rendering."""

import io
import json
import subprocess

from rich.console import Console

from cronenberg.cli.theme import (
    LIGHT,
    TOKYO_NIGHT,
    cc_output_mode,
    render_cc,
    render_hal,
    render_mi,
    render_raw,
    select_theme,
)

CLASSIFY = {"m.py": [{"rank": "A", "name": "classify", "complexity": 3}]}
CLASSIFY_SNAPSHOT = (
    "m.py\n"
    "╭──────┬──────────┬────────────╮\n"
    "│ Rank │ Name     │ Complexity │\n"
    "├──────┼──────────┼────────────┤\n"
    "│ A    │ classify │ 3          │\n"
    "╰──────┴──────────┴────────────╯\n"
)


def _console(theme, width=40):
    return Console(
        theme=theme,
        file=io.StringIO(),
        force_terminal=True,
        width=width,
        highlight=False,
        color_system="truecolor",
        no_color=False,
        record=True,
    )


def test_select_theme_from_colorfgbg():
    assert select_theme("auto", None) is TOKYO_NIGHT
    assert select_theme("auto", "") is TOKYO_NIGHT
    assert select_theme("auto", "15;0") is TOKYO_NIGHT
    assert select_theme("auto", "not-a-color") is TOKYO_NIGHT
    assert select_theme("auto", "0;15") is LIGHT
    assert select_theme("auto", "0;7") is LIGHT
    assert select_theme("tokyo-night", "0;15") is TOKYO_NIGHT
    assert select_theme("light", None) is LIGHT


def test_cc_output_mode_pipe_or_json_is_json():
    assert cc_output_mode(json=False, xml=False, md=False, is_tty=False) == "json"
    assert cc_output_mode(json=True, xml=False, md=False, is_tty=True) == "json"
    assert cc_output_mode(json=True, xml=True, md=True, is_tty=True) == "json"
    assert cc_output_mode(json=False, xml=True, md=False, is_tty=False) == "xml"
    assert cc_output_mode(json=False, xml=False, md=True, is_tty=False) == "md"
    assert cc_output_mode(json=False, xml=False, md=False, is_tty=True) == "rich"


def test_tty_snapshot_shows_rank_name_and_complexity():
    console = _console(TOKYO_NIGHT)
    render_cc(CLASSIFY, console)
    text = console.export_text(styles=False)
    raw = console.file.getvalue()

    assert text == CLASSIFY_SNAPSHOT
    assert "A" in text
    assert "classify" in text
    assert "3" in text
    assert "38;2;158;206;106m" in raw
    assert "38;2;192;202;245m" in raw
    assert "38;2;125;207;255m" in raw


def test_light_theme_uses_light_rank_color():
    console = _console(LIGHT)
    render_cc(CLASSIFY, console)

    assert "38;2;24;128;56m" in console.file.getvalue()


def test_render_keeps_block_order_within_groups():
    payload = {
        "z.py": [
            {
                "type": "class",
                "rank": "B",
                "name": "high",
                "complexity": 2,
                "methods": [
                    {
                        "type": "method",
                        "rank": "A",
                        "name": "inner",
                        "complexity": 1,
                        "classname": "high",
                    }
                ],
            },
            {"type": "function", "rank": "A", "name": "low", "complexity": 1},
            {
                "type": "class",
                "name": "Zed",
                "rank": "A",
                "complexity": 1,
                "methods": [
                    {
                        "type": "method",
                        "rank": "A",
                        "name": "tail",
                        "complexity": 1,
                        "classname": "Zed",
                    }
                ],
            },
            {"type": "function", "rank": "C", "name": "later", "complexity": 4},
        ]
    }
    console = _console(TOKYO_NIGHT, width=80)
    render_cc(payload, console)
    text = console.export_text(styles=False)

    assert text.index("high") < text.index("inner") < text.index("low") < text.index("later")
    assert text.index("later") < text.index("Zed")
    class_table, remainder = text.split("╯", 1)
    functions_table, late = remainder.split("╯", 1)
    assert "inner" in class_table
    assert "low" not in class_table
    assert "low" in functions_table
    assert "later" in functions_table
    assert "tail" not in functions_table
    assert "tail" in late


def test_two_classes_are_separate_titled_tables():
    payload = {
        "mod.py": [
            {
                "type": "class",
                "name": "Alpha",
                "rank": "A",
                "complexity": 1,
                "methods": [
                    {
                        "type": "method",
                        "rank": "A",
                        "name": "run",
                        "complexity": 1,
                        "classname": "Alpha",
                        "closures": [],
                    }
                ],
            },
            {
                "type": "class",
                "name": "Beta",
                "rank": "B",
                "complexity": 2,
                "methods": [
                    {
                        "type": "method",
                        "rank": "B",
                        "name": "run",
                        "complexity": 2,
                        "classname": "Beta",
                        "closures": [],
                    }
                ],
            },
        ]
    }
    console = _console(TOKYO_NIGHT, width=80)
    render_cc(payload, console)
    text = console.export_text(styles=False)

    alpha, beta = text.split("Beta", 1)
    assert "Alpha" in alpha
    assert alpha.count("run") == 1
    assert beta.count("run") == 1
    assert "╯" in alpha
    assert text.count("╭") == 2


def test_function_closure_renders_in_its_own_table():
    payload = {
        "mod.py": [
            {
                "type": "function",
                "rank": "B",
                "name": "outer",
                "complexity": 3,
                "closures": [
                    {
                        "type": "function",
                        "rank": "A",
                        "name": "inner",
                        "complexity": 1,
                        "closures": [],
                    }
                ],
            }
        ]
    }
    console = _console(TOKYO_NIGHT, width=80)
    render_cc(payload, console)
    text = console.export_text(styles=False)

    assert text.count("╭") == 2
    parent, closure = text.split("╯", 1)
    assert "outer" in parent
    assert "inner" not in parent
    title, table = closure.split("╭", 1)
    assert "outer" in title
    assert "inner" in table


def test_method_closure_renders_under_the_method_name():
    payload = {
        "mod.py": [
            {
                "type": "class",
                "name": "Alpha",
                "rank": "A",
                "complexity": 2,
                "methods": [
                    {
                        "type": "method",
                        "rank": "A",
                        "name": "run",
                        "complexity": 2,
                        "classname": "Alpha",
                        "closures": [
                            {
                                "type": "function",
                                "rank": "A",
                                "name": "helper",
                                "complexity": 1,
                                "closures": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    console = _console(TOKYO_NIGHT, width=80)
    render_cc(payload, console)
    text = console.export_text(styles=False)

    class_table, closure = text.split("╯", 1)
    assert "Alpha" in class_table
    assert "run" in class_table
    assert "helper" not in class_table
    title, table = closure.split("╭", 1)
    assert "run" in title
    assert "helper" in table


def test_raw_tty_snapshot_shows_metric_values():
    payload = {
        "mod.py": {
            "loc": 2,
            "lloc": 2,
            "sloc": 2,
            "comments": 0,
            "multi": 0,
            "blank": 0,
            "single_comments": 0,
        }
    }
    console = _console(TOKYO_NIGHT, width=40)
    render_raw(payload, console)
    text = console.export_text(styles=False)

    assert text == (
        "mod.py\n"
        "Metric           Value\n"
        "loc              2    \n"
        "lloc             2    \n"
        "sloc             2    \n"
        "comments         0    \n"
        "multi            0    \n"
        "blank            0    \n"
        "single_comments  0    \n"
    )
    assert "38;2;192;202;245m" in console.file.getvalue()
    assert text.index("loc") < text.index("lloc") < text.index("single_comments")


def test_mi_tty_snapshot_shows_rank_and_score():
    console = _console(TOKYO_NIGHT, width=40)
    render_mi({"mod.py": {"mi": 100.0, "rank": "A"}}, console)
    text = console.export_text(styles=False)

    assert text == "mod.py\nRank  MI   \nA     100.0\n"
    assert "A" in text
    assert "100.0" in text
    assert "38;2;158;206;106m" in console.file.getvalue()


def test_hal_tty_snapshot_shows_function_and_metrics():
    payload = {
        "mod.py": {
            "total": {"h1": 0, "bugs": 0.0},
            "functions": {"other": {"h1": 0, "bugs": 0.0}},
        }
    }
    console = _console(TOKYO_NIGHT, width=40)
    render_hal(payload, console)
    text = console.export_text(styles=False)

    assert text == (
        "mod.py\n"
        "      total       \n"
        "╭────────┬───────╮\n"
        "│ Metric │ Value │\n"
        "├────────┼───────┤\n"
        "│ h1     │ 0     │\n"
        "│ bugs   │ 0.0   │\n"
        "╰────────┴───────╯\n"
        "      other       \n"
        "╭────────┬───────╮\n"
        "│ Metric │ Value │\n"
        "├────────┼───────┤\n"
        "│ h1     │ 0     │\n"
        "│ bugs   │ 0.0   │\n"
        "╰────────┴───────╯\n"
    )
    assert "other" in text
    assert "h1" in text
    assert "0.0" in text
    assert text.index("total") < text.index("other")
    assert "38;2;192;202;245m" in console.file.getvalue()


def test_unknown_theme_is_a_usage_error(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("def low():\n    return 1\n")
    result = subprocess.run(
        ["cronenberg", "cc", str(source), "--theme", "solarized"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2


def test_xml_and_raw_pipes_stay_unrelated(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("def low():\n    return 1\n")
    xml = subprocess.run(
        ["cronenberg", "cc", str(source), "--xml"],
        check=False,
        capture_output=True,
        text=True,
    )
    raw = subprocess.run(
        ["cronenberg", "raw", str(source)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert xml.returncode == 0
    assert xml.stdout.startswith("<ccm>")
    assert raw.returncode == 0
    assert json.loads(raw.stdout)[str(source)]["loc"] == 2
