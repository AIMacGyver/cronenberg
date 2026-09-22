"""Rich themes for terminal command output."""

from collections.abc import Iterator

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ANSI white (7) and bright white (15). COLORFGBG's background is the last field.
_LIGHT_BACKGROUNDS = {7, 15}

TOKYO_NIGHT = Theme(
    {
        "cc.file": "bold #7aa2f7",
        "cc.name": "#c0caf5",
        "cc.complexity": "#7dcfff",
        "cc.rank.A": "bold #9ece6a",
        "cc.rank.B": "bold #9ece6a",
        "cc.rank.C": "bold #e0af68",
        "cc.rank.D": "bold #e0af68",
        "cc.rank.E": "bold #f7768e",
        "cc.rank.F": "bold #f7768e",
        "cc.error": "bold #f7768e",
    }
)

LIGHT = Theme(
    {
        "cc.file": "bold #1a73e8",
        "cc.name": "#202124",
        "cc.complexity": "#1967d2",
        "cc.rank.A": "bold #188038",
        "cc.rank.B": "bold #188038",
        "cc.rank.C": "bold #b06000",
        "cc.rank.D": "bold #b06000",
        "cc.rank.E": "bold #c5221f",
        "cc.rank.F": "bold #c5221f",
        "cc.error": "bold #c5221f",
    }
)

_THEMES = {
    "tokyo-night": TOKYO_NIGHT,
    "light": LIGHT,
}


def select_theme(name: str, colorfgbg: str | None = None) -> Theme:
    """Return the Rich theme for a terminal.

    Args:
        name: ``auto``, ``tokyo-night``, or ``light``.
        colorfgbg: ``COLORFGBG`` value, consulted only for ``auto``. The
            background is the last semicolon-separated integer. Backgrounds
            7 and 15 select the light theme. A missing, unparsable, or other
            value selects Tokyo Night.

    Returns:
        The theme to install on a Rich console.

    Raises:
        ValueError: If ``name`` is not a known theme.
    """
    if name == "auto":
        if _is_light_background(colorfgbg):
            return LIGHT
        return TOKYO_NIGHT
    try:
        return _THEMES[name]
    except KeyError:
        raise ValueError(name) from None


def _is_light_background(colorfgbg: str | None) -> bool:
    if not colorfgbg:
        return False
    background = colorfgbg.strip().split(";")[-1]
    try:
        return int(background) in _LIGHT_BACKGROUNDS
    except ValueError:
        return False


def cc_output_mode(*, json: bool, xml: bool, md: bool, is_tty: bool) -> str:
    """Choose how ``cc`` presents results.

    Args:
        json: Whether ``--json`` was set. This wins on a terminal and a pipe.
        xml: Whether ``--xml`` was set.
        md: Whether ``--md`` was set.
        is_tty: Whether the output stream is a terminal.

    Returns:
        ``json``, ``xml``, ``md``, or ``rich``. A pipe selects JSON. A
        terminal selects Rich unless a format flag is set.
    """
    if json:
        return "json"
    if xml:
        return "xml"
    if md:
        return "md"
    if not is_tty:
        return "json"
    return "rich"


def render_cc(payload: dict, console: Console) -> None:
    """Render a cc result dictionary.

    Args:
        payload: Filenames mapped to block lists or error records. File order
            and block list order are preserved.
        console: Console whose theme supplies ``cc.file``, ``cc.name``,
            ``cc.complexity``, and ``cc.rank`` styles.
    """
    for filename, blocks in payload.items():
        console.print(filename, style="cc.file")
        if isinstance(blocks, dict) and "error" in blocks:
            console.print(str(blocks["error"]), style="cc.error")
            continue
        table = Table(show_header=True, header_style="cc.file", box=None, pad_edge=False)
        table.add_column("Rank")
        table.add_column("Name")
        table.add_column("Complexity")
        for rank, block_name, complexity in _cc_rows(blocks):
            table.add_row(
                Text(rank, style=_rank_style(rank)),
                Text(block_name, style="cc.name"),
                Text(complexity, style="cc.complexity"),
            )
        console.print(table)


def render_raw(payload: dict, console: Console) -> None:
    """Render a raw-metrics dictionary.

    Args:
        payload: Filenames mapped to metric records or error records, in
            analysis order. Metric keys stay in record order.
        console: Console whose theme supplies ``cc.file``, ``cc.name``, and
            ``cc.complexity`` styles.
    """
    for filename, metrics in payload.items():
        console.print(filename, style="cc.file")
        if isinstance(metrics, dict) and "error" in metrics and "loc" not in metrics:
            console.print(str(metrics["error"]), style="cc.error")
            continue
        table = Table(show_header=True, header_style="cc.file", box=None, pad_edge=False)
        table.add_column("Metric")
        table.add_column("Value")
        for key, value in metrics.items():
            table.add_row(Text(str(key), style="cc.name"), Text(str(value), style="cc.complexity"))
        console.print(table)


def _cc_rows(blocks: object) -> Iterator[tuple[str, str, str]]:
    if not isinstance(blocks, list):
        return
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if "rank" in block and "name" in block:
            yield str(block["rank"]), str(block["name"]), str(block.get("complexity", ""))
        for key in ("methods", "closures"):
            yield from _cc_rows(block.get(key) or [])


def _rank_style(rank: str) -> str:
    style = f"cc.rank.{rank}"
    if style in TOKYO_NIGHT.styles:
        return style
    return "cc.name"
