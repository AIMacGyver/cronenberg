"""Tests for cc Rich themes and terminal rendering."""

import io
import subprocess

from rich.console import Console

from cronenberg.cli.theme import LIGHT, TOKYO_NIGHT, cc_output_mode, render_cc, select_theme

CLASSIFY = {"m.py": [{"rank": "A", "name": "classify", "complexity": 3}]}
CLASSIFY_SNAPSHOT = "m.py\nRank  Name      Complexity\nA     classify  3         \n"


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


def test_render_keeps_block_order_and_nested_methods():
    payload = {
        "z.py": [
            {
                "rank": "B",
                "name": "high",
                "complexity": 2,
                "methods": [{"rank": "A", "name": "inner", "complexity": 1}],
            },
            {"rank": "A", "name": "low", "complexity": 1},
        ]
    }
    console = _console(TOKYO_NIGHT, width=80)
    render_cc(payload, console)
    text = console.export_text(styles=False)

    assert text.index("high") < text.index("inner") < text.index("low")
    assert "\nB     high" in text
    assert "\nA     inner" in text
    assert "\nA     low" in text


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
    assert "LOC:" in raw.stdout
    assert not raw.stdout.lstrip().startswith("{")
