import subprocess
from importlib.metadata import distribution

from radon.complexity import cc_visit
from radon.raw import analyze

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
    assert [(entry_point.name, entry_point.value) for entry_point in console_scripts] == [("cronenberg", "radon:main")]


def test_installed_metadata_has_no_removed_plugin_entry_point():
    removed_group = "flake" + "8.extension"

    assert all(entry_point.group != removed_group for entry_point in distribution("cronenberg").entry_points)


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
