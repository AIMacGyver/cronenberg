import json
import os
import subprocess
import sys
from importlib.metadata import distribution

from cronenberg.complexity import cc_visit
from cronenberg.raw import analyze

SOURCE = """def classify(value):
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"
"""


def test_standalone_python_analysis():
    blocks = cc_visit(SOURCE)
    metrics = analyze(SOURCE)

    assert [(block.name, block.complexity) for block in blocks] == [("classify", 3)]
    assert metrics.sloc == 6


def test_standalone_cli_analysis(tmp_path):
    source_path = tmp_path / "example.py"
    source_path.write_text(SOURCE)

    result = subprocess.run(
        ["cronenberg", "cc", str(source_path), "-s"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert list(payload) == [str(source_path)]
    assert [(block["name"], block["complexity"], block["rank"]) for block in payload[str(source_path)]] == [
        ("classify", 3, "A")
    ]


def test_source_metadata_points_at_this_repository():
    project_urls = distribution("cronenberg").metadata.get_all("Project-URL") or []

    assert "Source, https://github.com/AIMacGyver/cronenberg" in project_urls
    assert all("github.com/rubik/radon" not in url for url in project_urls)


def test_installed_metadata_keeps_runtime_deps_without_obsolete_hooks():
    dist = distribution("cronenberg")
    requirements = dist.requires or []
    console_scripts = [entry_point for entry_point in dist.entry_points if entry_point.group == "console_scripts"]

    assert all(entry_point.group != "setuptools.installation" for entry_point in dist.entry_points)
    assert all(entry_point.name != "eggsecutable" for entry_point in dist.entry_points)
    assert "toml" not in (dist.metadata.get_all("Provides-Extra") or [])
    assert all("tomli" not in requirement for requirement in requirements)
    assert all(not requirement.startswith("mando") for requirement in requirements)
    assert all(not requirement.startswith("colorama") for requirement in requirements)
    assert any(requirement.startswith("typer") for requirement in requirements)
    assert any(requirement.startswith("rich") for requirement in requirements)
    assert [(entry_point.name, entry_point.value) for entry_point in console_scripts] == [
        ("cronenberg", "cronenberg:main"),
    ]


def test_installed_metadata_has_no_removed_plugin_entry_point():
    removed_group = "flake" + "8.extension"

    assert all(entry_point.group != removed_group for entry_point in distribution("cronenberg").entry_points)


CC_FLAGS = (
    "-n",
    "--min",
    "-x",
    "--max",
    "-s",
    "--show-complexity",
    "-a",
    "--average",
    "-e",
    "--exclude",
    "-i",
    "--ignore",
    "-o",
    "--order",
    "-j",
    "--json",
    "--no-assert",
    "--show-closures",
    "--total-average",
    "--xml",
    "--md",
    "-O",
    "--output-file",
    "--theme",
    "-h",
    "--help",
)


def test_cc_help_lists_existing_flags():
    help_result = subprocess.run(
        ["cronenberg", "cc", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    short_help = subprocess.run(
        ["cronenberg", "cc", "-h"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Usage: cronenberg cc" in help_result.stdout
    assert all(flag in help_result.stdout for flag in CC_FLAGS)
    assert "--json" in short_help.stdout
    assert short_help.returncode == 0


def test_cc_missing_paths_exits_2():
    result = subprocess.run(
        ["cronenberg", "cc"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2


def test_cc_config_min_still_filters(tmp_path):
    source_path = tmp_path / "mod.py"
    source_path.write_text("def low():\n    return 1\n")
    (tmp_path / "pyproject.toml").write_text('[tool.cronenberg]\ncc_min = "B"\n')
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env.pop("CRONENBERGCFG", None)

    hidden = subprocess.run(
        ["cronenberg", "cc", str(source_path), "-s"],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    shown = subprocess.run(
        ["cronenberg", "cc", str(source_path), "-s", "--min", "A"],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    assert hidden.returncode == 0
    assert json.loads(hidden.stdout) == {}
    assert shown.returncode == 0
    shown_payload = json.loads(shown.stdout)
    assert [(block["name"], block["rank"], block["complexity"]) for block in shown_payload[str(source_path)]] == [
        ("low", "A", 1)
    ]


RAW_FLAGS = (
    "-e",
    "--exclude",
    "-i",
    "--ignore",
    "-s",
    "--summary",
    "-j",
    "--json",
    "-O",
    "--output-file",
    "--theme",
    "-h",
    "--help",
)


def test_raw_help_lists_existing_flags():
    help_result = subprocess.run(
        ["cronenberg", "raw", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Usage: cronenberg raw" in help_result.stdout
    assert all(flag in help_result.stdout for flag in RAW_FLAGS)


def test_raw_fixture_matches_terminal_text_and_json(tmp_path):
    source_path = tmp_path / "mod.py"
    source_path.write_text("def other():\n    return 0\n")

    piped = subprocess.run(
        ["cronenberg", "raw", str(source_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    parsed_json = subprocess.run(
        ["cronenberg", "raw", str(source_path), "-j"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert piped.returncode == 0
    assert parsed_json.returncode == 0
    assert piped.stdout == parsed_json.stdout
    assert json.loads(piped.stdout) == {
        str(source_path): {
            "loc": 2,
            "lloc": 2,
            "sloc": 2,
            "comments": 0,
            "multi": 0,
            "blank": 0,
            "single_comments": 0,
        }
    }


MI_FLAGS = (
    "-n",
    "--min",
    "-x",
    "--max",
    "-m",
    "--multi",
    "-e",
    "--exclude",
    "-i",
    "--ignore",
    "-s",
    "--show",
    "-j",
    "--json",
    "--sort",
    "-O",
    "--output-file",
    "--theme",
    "-h",
    "--help",
)


def test_mi_help_lists_existing_flags():
    help_result = subprocess.run(
        ["cronenberg", "mi", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Usage: cronenberg mi" in help_result.stdout
    assert all(flag in help_result.stdout for flag in MI_FLAGS)


def test_mi_fixture_matches_terminal_text_and_json(tmp_path):
    source_path = tmp_path / "mod.py"
    source_path.write_text("def other():\n    return 0\n")
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env.pop("CRONENBERGCFG", None)

    piped = subprocess.run(
        ["cronenberg", "mi", str(source_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    parsed_json = subprocess.run(
        ["cronenberg", "mi", str(source_path), "-j"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )

    assert piped.returncode == 0
    assert parsed_json.returncode == 0
    assert piped.stdout == parsed_json.stdout
    assert json.loads(piped.stdout) == {str(source_path): {"mi": 100.0, "rank": "A"}}


def test_mi_multi_flag_inverts_the_default(tmp_path):
    source = 'def documented():\n    """doc"""\n    return 1\n'
    source_path = tmp_path / "mod.py"
    source_path.write_text(source)
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env.pop("CRONENBERGCFG", None)

    plain = subprocess.run(
        ["cronenberg", "mi", str(source_path), "-j"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    flagged = subprocess.run(
        ["cronenberg", "mi", str(source_path), "-j", "-m"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )

    from cronenberg.metrics import mi_visit

    assert plain.returncode == 0
    assert flagged.returncode == 0
    assert json.loads(plain.stdout)[str(source_path)]["mi"] == mi_visit(source, True)
    assert json.loads(flagged.stdout)[str(source_path)]["mi"] == mi_visit(source, False)


HAL_FLAGS = (
    "-e",
    "--exclude",
    "-i",
    "--ignore",
    "-j",
    "--json",
    "-f",
    "--functions",
    "-O",
    "--output-file",
    "--theme",
    "-h",
    "--help",
)

_HAL_ZEROS = {
    "h1": 0,
    "h2": 0,
    "N1": 0,
    "N2": 0,
    "vocabulary": 0,
    "length": 0,
    "calculated_length": 0,
    "volume": 0,
    "difficulty": 0,
    "effort": 0,
    "time": 0.0,
    "bugs": 0.0,
}


def test_hal_help_lists_existing_flags():
    help_result = subprocess.run(
        ["cronenberg", "hal", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    root = subprocess.run(
        ["cronenberg", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Usage: cronenberg hal" in help_result.stdout
    assert all(flag in help_result.stdout for flag in HAL_FLAGS)
    assert "Usage: cronenberg" in root.stdout
    assert "--version" in root.stdout
    for name in ("cc", "raw", "mi", "hal"):
        assert name in root.stdout


def test_root_without_args_shows_help():
    result = subprocess.run(
        ["cronenberg"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage: cronenberg" in result.stdout
    for name in ("cc", "raw", "mi", "hal"):
        assert name in result.stdout


def test_root_version_and_unknown_command():
    from cronenberg import __version__

    version = subprocess.run(
        ["cronenberg", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    short = subprocess.run(
        ["cronenberg", "-v"],
        check=False,
        capture_output=True,
        text=True,
    )
    unknown = subprocess.run(
        ["cronenberg", "nope"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert version.returncode == 0
    assert short.returncode == 0
    assert version.stdout.strip() == __version__
    assert short.stdout.strip() == __version__
    assert unknown.returncode == 2


def test_mando_and_colorama_are_not_importable():
    for module_name in ("mando", "colorama"):
        result = subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


def test_hal_fixture_matches_terminal_text_and_json(tmp_path):
    source_path = tmp_path / "mod.py"
    source_path.write_text("def other():\n    return 0\n")
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env.pop("CRONENBERGCFG", None)

    piped = subprocess.run(
        ["cronenberg", "hal", str(source_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    parsed_json = subprocess.run(
        ["cronenberg", "hal", str(source_path), "-j"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )

    assert piped.returncode == 0
    assert parsed_json.returncode == 0
    assert piped.stdout == parsed_json.stdout
    payload = json.loads(piped.stdout)
    assert payload[str(source_path)]["total"] == _HAL_ZEROS
    assert list(payload[str(source_path)]["functions"]) == ["other"]
    assert payload[str(source_path)]["functions"]["other"] == _HAL_ZEROS


def test_removed_hosted_integration_is_absent():
    help_result = subprocess.run(
        ["cronenberg", "cc", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    removed_option = "--code" + "climate"
    removed_host = "read" + "thedocs"
    project_urls = distribution("cronenberg").metadata.get_all("Project-URL") or []

    assert removed_option not in help_result.stdout
    assert all(removed_host not in url.lower() for url in project_urls)
