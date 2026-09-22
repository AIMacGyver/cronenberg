Cronenberg
==========

.. note::

    **Project status:** Cronenberg is an experimental modernization of
    `Radon <https://github.com/rubik/radon>`__. It currently focuses on
    packaging, developer tooling, and infrastructure. Metric output stays
    compatible with Radon. Cronenberg is not an official Radon replacement.

Cronenberg computes metrics from Python source code:

* **McCabe's complexity**, i.e. cyclomatic complexity
* **raw** metrics (these include SLOC, comment lines, blank lines, &c.)
* **Halstead** metrics (all of them)
* **Maintainability Index** (the one used in Visual Studio)

Cronenberg analyzes pure Python code. It does not analyze notebooks, ship a
Flake8 plugin, publish Read the Docs or Sphinx documentation, or integrate
with Code Climate.

Requirements
------------

Cronenberg requires **Python 3.11** or newer.

The ``cc`` command uses `Typer <https://typer.tiangolo.com/>`__ and
`Rich <https://rich.readthedocs.io/>`__. ``raw``, ``mi``, and ``hal`` use
`mando <https://github.com/rubik/mando>`__ and
`colorama <https://github.com/tartley/colorama>`__. If ``colorama`` cannot
be imported, those commands are not colored.

Installation
------------

Install the ``cronenberg`` distribution:

.. code-block:: sh

    $ pip install cronenberg

Or install from a source checkout:

.. code-block:: sh

    $ pip install .

The console script is ``cronenberg = cronenberg:main``. Commands use
``cronenberg``. The importable package is ``cronenberg``.

Usage
-----

Use the ``cronenberg`` command, or import the ``cronenberg`` package from
Python.

.. code-block:: sh

    $ cronenberg cc path/to/module.py
    $ cronenberg mi path/to/module.py
    $ cronenberg raw path/to/module.py
    $ cronenberg hal path/to/module.py

.. code-block:: python

    from cronenberg.complexity import cc_visit

Cyclomatic Complexity Example
-----------------------------

On a terminal, ``cc`` prints a Rich table of each block's rank, name, and
complexity. ``--theme`` is ``auto``, ``tokyo-night``, or ``light``. ``auto``
reads ``COLORFGBG`` when it is set and otherwise uses Tokyo Night. ANSI
backgrounds 7 and 15 select the light theme.

A pipe, ``--json``, or a non-terminal ``--output-file`` prints the same JSON
object. ``--xml`` and ``--md`` still write those formats. ``-n`` and ``-x``
still limit which ranks are included.

.. code-block:: text

    path/to/module.py
    Rank  Name      Complexity
    A     classify  3

**Note about file encoding**

On some systems, such as Windows, the default encoding is not UTF-8. To
analyze a Python file that contains Unicode characters, set
``CRONENBERGFILESENCODING`` to ``UTF-8``.

Configuration
-------------

Configuration uses ``cronenberg.cfg``, the ``[cronenberg]`` section,
``[tool.cronenberg]`` in ``pyproject.toml``, the ``CRONENBERGCFG`` environment
variable, and ``~/.cronenberg.cfg``.

On a Continuous Integration server
----------------------------------

Cronenberg reports metrics. It does not fail a build when a complexity
threshold is crossed. `Xenon <https://github.com/rubik/xenon>`__ is a
separate monitoring tool that exits with a non-zero status when thresholds
are surpassed.

Credits
-------

Michele Lacchia is the original author of Radon.

Links
-----

* Source: https://github.com/AIMacGyver/cronenberg
* Upstream Radon: https://github.com/rubik/radon
