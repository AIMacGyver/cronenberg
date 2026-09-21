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
