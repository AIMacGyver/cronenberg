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

It depends on `mando <https://github.com/rubik/mando>`__ for the command-line
interface and on `colorama <https://github.com/tartley/colorama>`__. If
``colorama`` cannot be imported, command output is not colored.

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

Quick example:

.. code-block:: sh

    $ cronenberg cc sympy/solvers/solvers.py -a -nc
    sympy/solvers/solvers.py
        F 346:0 solve - F
        F 1093:0 _solve - F
        F 1434:0 _solve_system - F
        F 2647:0 unrad - F
        F 110:0 checksol - F
        F 2238:0 _tsolve - F
        F 2482:0 _invert - F
        F 1862:0 solve_linear_system - E
        F 1781:0 minsolve_linear_system - D
        F 1636:0 solve_linear - D
        F 2382:0 nsolve - C

    11 blocks (classes, functions, methods) analyzed.
    Average complexity: F (61.0)

Explanation:

* ``cc`` computes cyclomatic complexity.
* ``-a`` calculates the average complexity at the end. The average is
  computed among the *shown* blocks. For the average among all blocks, use
  ``--total-average``.
* ``-nc`` prints only results with a complexity rank of C or worse. Other
  examples: ``-na`` (from A to F), or ``-nd`` (from D to F).
* The letter *in front of* the line numbers represents the type of the block
  (**F** means function, **M** method and **C** class).

Output can be colored:

.. image:: https://cloud.githubusercontent.com/assets/238549/3707477/5793aeaa-1435-11e4-98fb-00e0bd8137f5.png
    :alt: Colored cyclomatic complexity output

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
