import os
import subprocess
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

    assert result.stdout == (f"{source_path}\n    F 1:0 classify - A (3)\n")


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
    assert any(requirement.startswith("mando") for requirement in requirements)
    assert any(requirement.startswith("colorama") for requirement in requirements)
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
    assert hidden.stdout == ""
    assert shown.returncode == 0
    assert shown.stdout == f"{source_path}\n    F 1:0 low - A (1)\n"


def test_raw_mi_and_hal_stay_on_mando():
    root = subprocess.run(
        ["cronenberg", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_help = subprocess.run(
        ["cronenberg", "raw", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "usage: cronenberg" in root.stdout
    for name in ("cc", "raw", "mi", "hal"):
        assert name in root.stdout
    assert "usage: cronenberg raw" in raw_help.stdout
    assert "--json" in raw_help.stdout


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
