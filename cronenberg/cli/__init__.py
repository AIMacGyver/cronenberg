"""In this module the CLI interface is created."""

import configparser
import inspect
import os
import sys
import tomllib
from contextlib import contextmanager
from typing import Annotated, Literal

import typer
from rich.console import Console

import cronenberg.complexity as cc_mod
from cronenberg.cli.harvest import (
    CCHarvester,
    HCHarvester,
    MIHarvester,
    RawHarvester,
)
from cronenberg.cli.theme import cc_output_mode, render_cc, render_hal, render_mi, render_raw, select_theme

CONFIG_SECTION_NAME = "cronenberg"


class FileConfig:
    """
    Yield default options by reading local configuration files.
    """

    def __init__(self):
        self.file_cfg = self.file_config()

    def get_value(self, key, type, default):
        if not self.file_cfg.has_option(CONFIG_SECTION_NAME, key):
            return default
        # Equality-based dispatch is public behavior for type-like values.
        if type == int:  # noqa: E721
            return self.file_cfg.getint(CONFIG_SECTION_NAME, key, fallback=default)
        if type == bool:  # noqa: E721
            return self.file_cfg.getboolean(CONFIG_SECTION_NAME, key, fallback=default)
        else:
            return self.file_cfg.get(CONFIG_SECTION_NAME, key, fallback=default)

    @staticmethod
    def toml_config():
        try:
            with open("pyproject.toml", "rb") as pyproject_file:
                pyproject = tomllib.load(pyproject_file)
            config_dict = pyproject["tool"]
        except tomllib.TOMLDecodeError as exc:
            raise exc
        except Exception:
            config_dict = {}
        return config_dict

    @staticmethod
    def file_config():
        """Return any file configuration discovered"""
        config = configparser.ConfigParser()
        for path in (os.getenv("CRONENBERGCFG", None), "cronenberg.cfg"):
            if path is not None and os.path.exists(path):
                config.read_file(open(path))
        config.read_dict(FileConfig.toml_config())
        config.read([os.path.expanduser("~/.cronenberg.cfg")])
        return config


_cfg = FileConfig()


def _print_version(value: bool) -> None:
    """Print the package version and exit when the version flag is present.

    Args:
        value: Whether ``-v`` or ``--version`` was passed.
    """
    if value:
        typer.echo(sys.modules["cronenberg"].__version__)
        raise typer.Exit()


app = typer.Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show the version and exit.",
            callback=_print_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Code Metrics in Python."""

_MI_MULTI_DEFAULT = _cfg.get_value("multi", bool, True)
_MI_SHOW_DEFAULT = _cfg.get_value("show_mi", bool, False)
_HAL_FUNCTIONS_DEFAULT = _cfg.get_value("functions", bool, False)


def _mando_bool(default: bool, given: bool) -> bool:
    """Resolve a boolean flag the way mando did.

    Args:
        default: Value used when the flag is absent.
        given: Whether the flag was present.

    Returns:
        ``default`` when the flag is absent, otherwise its opposite.
    """
    if given:
        return not default
    return default


def cc(
    paths,
    min=_cfg.get_value("cc_min", str, "A"),
    max=_cfg.get_value("cc_max", str, "F"),
    show_complexity=_cfg.get_value("show_complexity", bool, False),
    average=_cfg.get_value("average", bool, False),
    exclude=_cfg.get_value("exclude", str, None),
    ignore=_cfg.get_value("ignore", str, None),
    order=_cfg.get_value("order", str, "SCORE"),
    json=False,
    no_assert=_cfg.get_value("no_assert", bool, False),
    show_closures=_cfg.get_value("show_closures", bool, False),
    total_average=_cfg.get_value("total_average", bool, False),
    xml=False,
    md=False,
    output_file=_cfg.get_value("output_file", str, None),
    theme="auto",
):
    """Analyze the given Python modules and compute Cyclomatic
    Complexity (CC).

    A terminal shows a Rich table of rank, name, and complexity. A pipe or
    ``--json`` prints one JSON object. ``--xml`` and ``--md`` stay available.

    The output can be filtered using the *min* and *max* flags.

    :param paths: The paths where to find modules or packages to analyze. More
        than one path is allowed.
    :param -n, --min <str>: The minimum complexity to display (default to A).
    :param -x, --max <str>: The maximum complexity to display (default to F).
    :param -e, --exclude <str>: Exclude files only when their path matches one
        of these glob patterns. Usually needs quoting at the command line.
    :param -i, --ignore <str>: Ignore directories when their name matches one
        of these glob patterns: cronenberg won't even descend into them. By default,
        hidden directories (starting with '.') are ignored.
    :param -s, --show-complexity: Whether or not to show the actual complexity
        score together with the A-F rank. Default to False.
    :param -a, --average: If True, at the end of the analysis display the
        average complexity. Default to False.
    :param --total-average: Like `-a, --average`, but it is not influenced by
        `min` and `max`. Every analyzed block is counted, no matter whether it
        is displayed or not.
    :param -o, --order <str>: The ordering function. Can be SCORE, LINES or
        ALPHA.
    :param -j, --json: Format results in JSON.
    :param --xml: Format results in XML (compatible with CCM).
    :param --md: Format results in Markdown.
    :param --no-assert: Do not count `assert` statements when computing
        complexity.
    :param --show-closures: Add closures/inner classes to the output.
    :param -O, --output-file <str>: The output file (default to stdout).
    :param --theme <str>: ``auto``, ``tokyo-night``, or ``light``. ``auto``
        uses ``COLORFGBG`` when set, otherwise Tokyo Night.
    """
    config = Config(
        min=min.upper(),
        max=max.upper(),
        exclude=exclude,
        ignore=ignore,
        show_complexity=show_complexity,
        average=average,
        total_average=total_average,
        order=getattr(cc_mod, order.upper(), getattr(cc_mod, "SCORE")),
        no_assert=no_assert,
        show_closures=show_closures,
    )
    harvester = CCHarvester(paths, config)
    with outstream(output_file) as stream:
        mode = cc_output_mode(json=json, xml=xml, md=md, is_tty=stream.isatty())
        if mode == "rich":
            console = Console(
                theme=select_theme(theme, os.environ.get("COLORFGBG")),
                file=stream,
                highlight=False,
            )
            render_cc(harvester.as_dict(), console)
            return
        log_result(
            harvester,
            json=mode == "json",
            xml=mode == "xml",
            md=mode == "md",
            stream=stream,
        )


@app.command("cc")
def _cc_command(
    paths: Annotated[
        list[str],
        typer.Argument(
            help=(
                "The paths where to find modules or packages to analyze. More "
                "than one path is allowed."
            )
        ),
    ],
    min: Annotated[
        str,
        typer.Option("--min", "-n", help="The minimum complexity to display (default to A)."),
    ] = _cfg.get_value("cc_min", str, "A"),
    max: Annotated[
        str,
        typer.Option("--max", "-x", help="The maximum complexity to display (default to F)."),
    ] = _cfg.get_value("cc_max", str, "F"),
    show_complexity: Annotated[
        bool,
        typer.Option(
            "--show-complexity",
            "-s",
            help="Whether or not to show the actual complexity score together with the A-F rank. Default to False.",
        ),
    ] = _cfg.get_value("show_complexity", bool, False),
    average: Annotated[
        bool,
        typer.Option(
            "--average",
            "-a",
            help="If True, at the end of the analysis display the average complexity. Default to False.",
        ),
    ] = _cfg.get_value("average", bool, False),
    exclude: Annotated[
        str | None,
        typer.Option(
            "--exclude",
            "-e",
            help=(
                "Exclude files only when their path matches one of these glob "
                "patterns. Usually needs quoting at the command line."
            ),
        ),
    ] = _cfg.get_value("exclude", str, None),
    ignore: Annotated[
        str | None,
        typer.Option(
            "--ignore",
            "-i",
            help=(
                "Ignore directories when their name matches one of these glob "
                "patterns: cronenberg won't even descend into them. By default, "
                "hidden directories (starting with '.') are ignored."
            ),
        ),
    ] = _cfg.get_value("ignore", str, None),
    order: Annotated[
        str,
        typer.Option("--order", "-o", help="The ordering function. Can be SCORE, LINES or ALPHA."),
    ] = _cfg.get_value("order", str, "SCORE"),
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Format results in JSON.")] = False,
    no_assert: Annotated[
        bool,
        typer.Option("--no-assert", help="Do not count `assert` statements when computing complexity."),
    ] = _cfg.get_value("no_assert", bool, False),
    show_closures: Annotated[
        bool,
        typer.Option("--show-closures", help="Add closures/inner classes to the output."),
    ] = _cfg.get_value("show_closures", bool, False),
    total_average: Annotated[
        bool,
        typer.Option(
            "--total-average",
            help=(
                "Like -a, --average, but it is not influenced by min and max. "
                "Every analyzed block is counted, no matter whether it is displayed or not."
            ),
        ),
    ] = _cfg.get_value("total_average", bool, False),
    xml: Annotated[
        bool,
        typer.Option("--xml", help="Format results in XML (compatible with CCM)."),
    ] = False,
    md: Annotated[bool, typer.Option("--md", help="Format results in Markdown.")] = False,
    output_file: Annotated[
        str | None,
        typer.Option("--output-file", "-O", help="The output file (default to stdout)."),
    ] = _cfg.get_value("output_file", str, None),
    theme: Annotated[
        Literal["auto", "tokyo-night", "light"],
        typer.Option(
            "--theme",
            help="Color theme. auto uses COLORFGBG when set, otherwise Tokyo Night.",
        ),
    ] = "auto",
):
    """Analyze the given Python modules and compute Cyclomatic Complexity (CC).

    A terminal shows a Rich table of rank, name, and complexity. A pipe or
    --json prints one JSON object.
    """
    cc(
        paths,
        min=min,
        max=max,
        show_complexity=show_complexity,
        average=average,
        exclude=exclude,
        ignore=ignore,
        order=order,
        json=json_output,
        no_assert=no_assert,
        show_closures=show_closures,
        total_average=total_average,
        xml=xml,
        md=md,
        output_file=output_file,
        theme=theme,
    )


def raw(
    paths,
    exclude=_cfg.get_value("exclude", str, None),
    ignore=_cfg.get_value("ignore", str, None),
    summary=False,
    json=False,
    output_file=_cfg.get_value("output_file", str, None),
    theme="auto",
):
    """Analyze the given Python modules and compute raw metrics.

    A terminal shows a Rich table of the JSON metrics. A pipe or ``--json``
    prints one JSON object. The summary is not part of that object.

    :param paths: The paths where to find modules or packages to analyze. More
        than one path is allowed.
    :param -e, --exclude <str>: Exclude files only when their path matches one
        of these glob patterns. Usually needs quoting at the command line.
    :param -i, --ignore <str>: Ignore directories when their name matches one
        of these glob patterns: cronenberg won't even descend into them. By default,
        hidden directories (starting with '.') are ignored.
    :param -s, --summary:  If given, at the end of the analysis display the
        summary of the gathered metrics. Default to False.
    :param -j, --json: Format results in JSON. Note that the JSON export does
        not include the summary (enabled with `-s, --summary`).
    :param -O, --output-file <str>: The output file (default to stdout).
    :param --theme <str>: ``auto``, ``tokyo-night``, or ``light``. ``auto``
        uses ``COLORFGBG`` when set, otherwise Tokyo Night.
    """
    config = Config(
        exclude=exclude,
        ignore=ignore,
        summary=summary,
    )
    harvester = RawHarvester(paths, config)
    with outstream(output_file) as stream:
        mode = cc_output_mode(json=json, xml=False, md=False, is_tty=stream.isatty())
        if mode == "rich":
            console = Console(
                theme=select_theme(theme, os.environ.get("COLORFGBG")),
                file=stream,
                highlight=False,
            )
            render_raw(harvester.as_dict(), console)
            return
        log_result(harvester, json=mode == "json", stream=stream)


@app.command("raw")
def _raw_command(
    paths: Annotated[
        list[str],
        typer.Argument(
            help=(
                "The paths where to find modules or packages to analyze. More "
                "than one path is allowed."
            )
        ),
    ],
    exclude: Annotated[
        str | None,
        typer.Option(
            "--exclude",
            "-e",
            help=(
                "Exclude files only when their path matches one of these glob "
                "patterns. Usually needs quoting at the command line."
            ),
        ),
    ] = _cfg.get_value("exclude", str, None),
    ignore: Annotated[
        str | None,
        typer.Option(
            "--ignore",
            "-i",
            help=(
                "Ignore directories when their name matches one of these glob "
                "patterns: cronenberg won't even descend into them. By default, "
                "hidden directories (starting with '.') are ignored."
            ),
        ),
    ] = _cfg.get_value("ignore", str, None),
    summary: Annotated[
        bool,
        typer.Option(
            "--summary",
            "-s",
            help="If given, at the end of the analysis display the summary of the gathered metrics. Default to False.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Format results in JSON. The JSON export does not include the summary.",
        ),
    ] = False,
    output_file: Annotated[
        str | None,
        typer.Option("--output-file", "-O", help="The output file (default to stdout)."),
    ] = _cfg.get_value("output_file", str, None),
    theme: Annotated[
        Literal["auto", "tokyo-night", "light"],
        typer.Option(
            "--theme",
            help="Color theme. auto uses COLORFGBG when set, otherwise Tokyo Night.",
        ),
    ] = "auto",
):
    """Analyze the given Python modules and compute raw metrics.

    A terminal shows a Rich table of the JSON metrics. A pipe or --json
    prints one JSON object.
    """
    raw(
        paths,
        exclude=exclude,
        ignore=ignore,
        summary=summary,
        json=json_output,
        output_file=output_file,
        theme=theme,
    )


def mi(
    paths,
    min=_cfg.get_value("mi_min", str, "A"),
    max=_cfg.get_value("mi_max", str, "C"),
    multi=_MI_MULTI_DEFAULT,
    exclude=_cfg.get_value("exclude", str, None),
    ignore=_cfg.get_value("ignore", str, None),
    show=_MI_SHOW_DEFAULT,
    json=False,
    sort=False,
    output_file=_cfg.get_value("output_file", str, None),
    theme="auto",
):
    """Analyze the given Python modules and compute the Maintainability Index.

    A terminal shows a Rich table of rank and MI from the JSON object. A pipe
    or ``--json`` prints that object. The maintainability index (MI) is a
    compound metric, with the primary aim being to determine how easy it will
    be to maintain a particular body of code.

    :param paths: The paths where to find modules or packages to analyze. More
        than one path is allowed.
    :param -n, --min <str>: The minimum MI to display (default to A).
    :param -x, --max <str>: The maximum MI to display (default to C).
    :param -e, --exclude <str>: Exclude files only when their path matches one
        of these glob patterns. Usually needs quoting at the command line.
    :param -i, --ignore <str>: Ignore directories when their name matches one
        of these glob patterns: cronenberg won't even descend into them. By default,
        hidden directories (starting with '.') are ignored.
    :param -m, --multi: If given, multiline strings are not counted as
        comments.
    :param -s, --show: If given, the actual MI value is shown in results.
    :param -j, --json: Format results in JSON.
    :param --sort: If given, results are sorted in ascending order.
    :param -O, --output-file <str>: The output file (default to stdout).
    :param --theme <str>: ``auto``, ``tokyo-night``, or ``light``. ``auto``
        uses ``COLORFGBG`` when set, otherwise Tokyo Night.
    """
    config = Config(
        min=min.upper(),
        max=max.upper(),
        exclude=exclude,
        ignore=ignore,
        multi=multi,
        show=show,
        sort=sort,
    )

    harvester = MIHarvester(paths, config)
    with outstream(output_file) as stream:
        mode = cc_output_mode(json=json, xml=False, md=False, is_tty=stream.isatty())
        if mode == "rich":
            console = Console(
                theme=select_theme(theme, os.environ.get("COLORFGBG")),
                file=stream,
                highlight=False,
            )
            render_mi(harvester.as_dict(), console)
            return
        log_result(harvester, json=mode == "json", stream=stream)


@app.command("mi")
def _mi_command(
    paths: Annotated[
        list[str],
        typer.Argument(
            help=(
                "The paths where to find modules or packages to analyze. More "
                "than one path is allowed."
            )
        ),
    ],
    min: Annotated[
        str,
        typer.Option("--min", "-n", help="The minimum MI to display (default to A)."),
    ] = _cfg.get_value("mi_min", str, "A"),
    max: Annotated[
        str,
        typer.Option("--max", "-x", help="The maximum MI to display (default to C)."),
    ] = _cfg.get_value("mi_max", str, "C"),
    multi: Annotated[
        bool,
        typer.Option(
            "--multi",
            "-m",
            help="If given, multiline strings are not counted as comments.",
        ),
    ] = False,
    exclude: Annotated[
        str | None,
        typer.Option(
            "--exclude",
            "-e",
            help=(
                "Exclude files only when their path matches one of these glob "
                "patterns. Usually needs quoting at the command line."
            ),
        ),
    ] = _cfg.get_value("exclude", str, None),
    ignore: Annotated[
        str | None,
        typer.Option(
            "--ignore",
            "-i",
            help=(
                "Ignore directories when their name matches one of these glob "
                "patterns: cronenberg won't even descend into them. By default, "
                "hidden directories (starting with '.') are ignored."
            ),
        ),
    ] = _cfg.get_value("ignore", str, None),
    show: Annotated[
        bool,
        typer.Option("--show", "-s", help="If given, the actual MI value is shown in results."),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Format results in JSON.")] = False,
    sort: Annotated[bool, typer.Option("--sort", help="If given, results are sorted in ascending order.")] = False,
    output_file: Annotated[
        str | None,
        typer.Option("--output-file", "-O", help="The output file (default to stdout)."),
    ] = _cfg.get_value("output_file", str, None),
    theme: Annotated[
        Literal["auto", "tokyo-night", "light"],
        typer.Option(
            "--theme",
            help="Color theme. auto uses COLORFGBG when set, otherwise Tokyo Night.",
        ),
    ] = "auto",
):
    """Analyze the given Python modules and compute the Maintainability Index.

    A terminal shows a Rich table of rank and MI. A pipe or --json prints one
    JSON object.
    """
    mi(
        paths,
        min=min,
        max=max,
        multi=_mando_bool(_MI_MULTI_DEFAULT, multi),
        exclude=exclude,
        ignore=ignore,
        show=_mando_bool(_MI_SHOW_DEFAULT, show),
        json=json_output,
        sort=_mando_bool(False, sort),
        output_file=output_file,
        theme=theme,
    )


def hal(
    paths,
    exclude=_cfg.get_value("exclude", str, None),
    ignore=_cfg.get_value("ignore", str, None),
    json=False,
    functions=_HAL_FUNCTIONS_DEFAULT,
    output_file=_cfg.get_value("output_file", str, None),
    theme="auto",
):
    """Analyze the given Python modules and compute their Halstead metrics.

    A terminal shows a Rich table of the JSON object's total and function
    metrics. A pipe or ``--json`` prints that object.

    The Halstead metrics are a series of measurements meant to quantitatively
    measure the complexity of code, including the difficulty a programmer would
    have in writing it.

    :param paths: The paths where to find modules or packages to analyze. More
        than one path is allowed.
    :param -e, --exclude <str>: Exclude files only when their path matches one
        of these glob patterns. Usually needs quoting at the command line.
    :param -i, --ignore <str>: Ignore directories when their name matches one
        of these glob patterns: cronenberg won't even descend into them. By default,
        hidden directories (starting with '.') are ignored.
    :param -j, --json: Format results in JSON.
    :param -f, --functions: Analyze files by top-level functions instead of as
        a whole.
    :param -O, --output-file <str>: The output file (default to stdout).
    :param --theme <str>: ``auto``, ``tokyo-night``, or ``light``. ``auto``
        uses ``COLORFGBG`` when set, otherwise Tokyo Night.
    """
    config = Config(
        exclude=exclude,
        ignore=ignore,
        by_function=functions,
    )

    harvester = HCHarvester(paths, config)
    with outstream(output_file) as stream:
        mode = cc_output_mode(json=json, xml=False, md=False, is_tty=stream.isatty())
        if mode == "rich":
            console = Console(
                theme=select_theme(theme, os.environ.get("COLORFGBG")),
                file=stream,
                highlight=False,
            )
            render_hal(harvester.as_dict(), console)
            return
        log_result(harvester, json=mode == "json", xml=False, md=False, stream=stream)


@app.command("hal")
def _hal_command(
    paths: Annotated[
        list[str],
        typer.Argument(
            help=(
                "The paths where to find modules or packages to analyze. More "
                "than one path is allowed."
            )
        ),
    ],
    exclude: Annotated[
        str | None,
        typer.Option(
            "--exclude",
            "-e",
            help=(
                "Exclude files only when their path matches one of these glob "
                "patterns. Usually needs quoting at the command line."
            ),
        ),
    ] = _cfg.get_value("exclude", str, None),
    ignore: Annotated[
        str | None,
        typer.Option(
            "--ignore",
            "-i",
            help=(
                "Ignore directories when their name matches one of these glob "
                "patterns: cronenberg won't even descend into them. By default, "
                "hidden directories (starting with '.') are ignored."
            ),
        ),
    ] = _cfg.get_value("ignore", str, None),
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Format results in JSON.")] = False,
    functions: Annotated[
        bool,
        typer.Option(
            "--functions",
            "-f",
            help="Analyze files by top-level functions instead of as a whole.",
        ),
    ] = False,
    output_file: Annotated[
        str | None,
        typer.Option("--output-file", "-O", help="The output file (default to stdout)."),
    ] = _cfg.get_value("output_file", str, None),
    theme: Annotated[
        Literal["auto", "tokyo-night", "light"],
        typer.Option(
            "--theme",
            help="Color theme. auto uses COLORFGBG when set, otherwise Tokyo Night.",
        ),
    ] = "auto",
):
    """Analyze the given Python modules and compute their Halstead metrics.

    A terminal shows a Rich table of the JSON metrics. A pipe or --json prints
    one JSON object.
    """
    hal(
        paths,
        exclude=exclude,
        ignore=ignore,
        json=json_output,
        functions=_mando_bool(_HAL_FUNCTIONS_DEFAULT, functions),
        output_file=output_file,
        theme=theme,
    )


class Config:
    """An object holding config values."""

    def __init__(self, **kwargs):
        """Configuration values are passed as keyword parameters."""
        self.config_values = kwargs

    def __getattr__(self, attr):
        """If an attribute is not found inside the config values, the request
        is handed to `__getattribute__`.
        """
        if attr in self.config_values:
            return self.config_values[attr]
        return self.__getattribute__(attr)

    def __repr__(self):
        """The string representation of the Config object is just the one of
        the dictionary holding the configuration values.
        """
        return repr(self.config_values)

    def __eq__(self, other):
        """Two Config objects are equals if their contents are equal."""
        return self.config_values == other.config_values

    @classmethod
    def from_function(cls, func):
        """Construct a Config object from a function's defaults."""
        kwonlydefaults = {}
        try:
            argspec = inspect.getfullargspec(func)
            kwonlydefaults = argspec.kwonlydefaults or {}
        except AttributeError:  # pragma: no cover
            argspec = inspect.getargspec(func)
        args, _, _, defaults = argspec[:4]
        values = dict(zip(reversed(args), reversed(defaults or [])))
        values.update(kwonlydefaults)
        return cls(**values)


def log_result(harvester, **kwargs):
    """Log JSON, XML, or Markdown from a harvester.

    Args:
        harvester: Object with ``as_json``, ``as_xml``, and ``as_md``.
        **kwargs: ``json``, ``xml``, and ``md`` select the formatter. ``json``
            wins when more than one is set. Remaining keywords, including
            ``stream``, are passed to :func:`log`.
    """
    if kwargs.get("json"):
        log(harvester.as_json(), noformat=True, **kwargs)
    elif kwargs.get("xml"):
        log(harvester.as_xml(), noformat=True, **kwargs)
    elif kwargs.get("md"):
        log(harvester.as_md(), noformat=True, **kwargs)


def log(msg, *args, **kwargs):
    """Log a message, passing *args* to the strings' `format()` method.

    *indent*, if present as a keyword argument, specifies the indent level, so
    that `indent=0` will log normally, `indent=1` will indent the message by 4
    spaces, &c..
    *noformat*, if present and True, will cause the message not to be formatted
    in any way.
    """
    indent = 4 * kwargs.get("indent", 0)
    delimiter = kwargs.get("delimiter", "\n")
    m = msg if kwargs.get("noformat", False) else msg.format(*args)
    stream = kwargs.get("stream", sys.stdout)
    stream.write(" " * indent + m + delimiter)


def log_list(lst, *args, **kwargs):
    """Log an entire list, line by line. All the arguments are directly passed
    to :func:`~cronenberg.cli.log`.
    """
    for line in lst:
        log(line, *args, **kwargs)


def log_error(msg, *args, **kwargs):
    """Log an error message. Arguments are the same as log()."""
    log(f"ERROR: {msg}", *args, **kwargs)


@contextmanager
def outstream(outfile=None):
    """Encapsulate output stream creation as a context manager"""
    if outfile:
        with open(outfile, "w") as outstream:
            yield outstream
    else:
        yield sys.stdout
