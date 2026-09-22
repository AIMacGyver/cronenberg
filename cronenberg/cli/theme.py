"""Rich themes for terminal command output."""

from rich import box
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
    """Render cyclomatic complexity as one Rich table per group.

    The file path stays a heading. Module-level functions share one table.
    Each class is a table titled with the class name, and its methods are the
    rows. Closures of a function or method are a separate table under that
    name. Block order is preserved within each group.

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
        _render_cc_groups(blocks, console)


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


def render_mi(payload: dict, console: Console) -> None:
    """Render a Maintainability Index dictionary.

    Args:
        payload: Filenames mapped to MI records or error records, in analysis
            order.
        console: Console whose theme supplies rank and metric styles.
    """
    for filename, record in payload.items():
        console.print(filename, style="cc.file")
        if isinstance(record, dict) and "error" in record and "rank" not in record:
            console.print(str(record["error"]), style="cc.error")
            continue
        table = Table(show_header=True, header_style="cc.file", box=None, pad_edge=False)
        table.add_column("Rank")
        table.add_column("MI")
        rank = str(record.get("rank", ""))
        table.add_row(Text(rank, style=_rank_style(rank)), Text(str(record.get("mi", "")), style="cc.complexity"))
        console.print(table)


def render_hal(payload: dict, console: Console) -> None:
    """Render Halstead metrics as one table for the total and one per function.

    The file path stays a heading. The module total is one table, followed by
    a table for each function in record order.

    Args:
        payload: Filenames mapped to ``total`` and ``functions`` records, in
            analysis order. Function names stay in record order.
        console: Console whose theme supplies file, name, and metric styles.
    """
    for filename, record in payload.items():
        console.print(filename, style="cc.file")
        if isinstance(record, dict) and "error" in record and "total" not in record:
            console.print(str(record["error"]), style="cc.error")
            continue
        _print_metric_table(console, record.get("total") or {}, title="total")
        for function_name, metrics in (record.get("functions") or {}).items():
            _print_metric_table(console, metrics, title=str(function_name))


def _print_metric_table(console: Console, metrics: dict, title: str | None = None) -> None:
    table = _bordered_table(title)
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in metrics.items():
        table.add_row(Text(str(key), style="cc.name"), Text(str(value), style="cc.complexity"))
    console.print(table)


def _bordered_table(title: str | None = None) -> Table:
    return Table(
        title=title,
        title_style="cc.name",
        show_header=True,
        header_style="cc.file",
        box=box.ROUNDED,
    )


def _render_cc_groups(blocks: object, console: Console) -> None:
    if not isinstance(blocks, list):
        return
    entries = [block for block in blocks if isinstance(block, dict)]
    functions: list[dict] = []
    class_rows: dict[str, list[dict]] = {}
    sequence: list[tuple[str, str | None]] = []
    seen_classes: set[str] = set()
    seen_functions = False
    for block in entries:
        if _is_class_block(block):
            name = str(block.get("name", ""))
            if name not in seen_classes:
                sequence.append(("class", name))
                seen_classes.add(name)
                class_rows[name] = []
            for method in block.get("methods") or []:
                if isinstance(method, dict):
                    class_rows[name].append(method)
        elif _is_method_block(block):
            name = str(block.get("classname") or "")
            if name not in seen_classes:
                sequence.append(("class", name))
                seen_classes.add(name)
                class_rows[name] = []
            class_rows[name].append(block)
        else:
            functions.append(block)
            if not seen_functions:
                sequence.append(("functions", None))
                seen_functions = True
    for kind, name in sequence:
        if kind == "functions":
            _print_cc_table(console, functions)
            for function in functions:
                _render_closure_tables(function, console)
            continue
        methods = class_rows[name or ""]
        _print_cc_table(console, methods, title=name)
        for method in methods:
            _render_closure_tables(method, console)


def _print_cc_table(console: Console, rows: list[dict], title: str | None = None) -> None:
    table = _bordered_table(title)
    table.add_column("Rank")
    table.add_column("Name")
    table.add_column("Complexity")
    for block in rows:
        rank = str(block.get("rank", ""))
        table.add_row(
            Text(rank, style=_rank_style(rank)),
            Text(str(block.get("name", "")), style="cc.name"),
            Text(str(block.get("complexity", "")), style="cc.complexity"),
        )
    console.print(table)


def _render_closure_tables(block: dict, console: Console) -> None:
    closures = [closure for closure in (block.get("closures") or []) if isinstance(closure, dict)]
    if not closures:
        return
    _print_cc_table(console, closures, title=str(block.get("name", "")))
    for closure in closures:
        _render_closure_tables(closure, console)


def _is_class_block(block: dict) -> bool:
    return block.get("type") == "class" or "methods" in block


def _is_method_block(block: dict) -> bool:
    return block.get("type") == "method" or bool(block.get("classname"))


def _rank_style(rank: str) -> str:
    style = f"cc.rank.{rank}"
    if style in TOKYO_NIGHT.styles:
        return style
    return "cc.name"
