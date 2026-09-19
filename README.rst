Radon
=====

.. note::

    **Project status:** Cronenberg is an experimental modernization of
    `Radon <https://github.com/rubik/radon>`__. It currently focuses on
    packaging, developer tooling, and infrastructure while preserving
    behavior. Cronenberg is not yet an official Radon replacement.

.. image:: https://img.shields.io/coveralls/rubik/radon/master.svg?style=for-the-badge
    :alt: Coveralls badge
    :target: https://coveralls.io/r/rubik/radon?branch=master

.. image:: https://img.shields.io/pypi/v/radon.svg?style=for-the-badge
    :alt: PyPI latest version badge
    :target: https://pypi.python.org/pypi/radon

.. image:: https://img.shields.io/pypi/l/radon.svg?style=for-the-badge
    :alt: Radon license
    :target: https://pypi.python.org/pypi/radon

.. raw::  html

    <p><a href="https://hellogithub.com/repository/bbca7606a6b1412da1312d68ae81d781" target="_blank"><img src="https://abroad.hellogithub.com/v1/widgets/recommend.svg?rid=bbca7606a6b1412da1312d68ae81d781&claim_uid=pO5Q0JkFzC8IPr9&theme=dark" alt="Featured｜HelloGitHub" style="width: 250px; height: 54px;" width="250" height="54" /></a></p>

----

Radon is a Python tool that computes various metrics from the source code.
Radon can compute:

* **McCabe's complexity**, i.e. cyclomatic complexity
* **raw** metrics (these include SLOC, comment lines, blank lines, &c.)
* **Halstead** metrics (all of them)
* **Maintainability Index** (the one used in Visual Studio)

Requirements
------------

Radon will run from **Python 2.7** to **Python 3.12** (except Python versions
from 3.0 to 3.3) with a single code base and without the need of tools like
2to3 or six. It can also run on **PyPy** without any problems (currently PyPy
3.5 v7.3.1 is used in tests).

Radon depends on as few packages as possible. Currently only `mando` is
strictly required (for the CLI interface). `colorama` is also listed as a
dependency but if Radon cannot import it, the output simply will not be
colored.

**Note**:
**Python 2.6** was supported until version 1.5.0. Starting from version 2.0, it
is not supported anymore.

Installation
------------

With Pip:

.. code-block:: sh

    $ pip install radon

If you want to configure Radon from `pyproject.toml` and you run Python <3.11,
you'll need the extra `toml` dependency:

.. code-block:: sh

   $ pip install radon[toml]

Or install from a source checkout:

.. code-block:: sh

    $ pip install .

Usage
-----

Radon can be used either from the command line or programmatically.
Documentation is at https://radon.readthedocs.org/.

Cyclomatic Complexity Example
-----------------------------

Save the following as ``example.py``:

.. code-block:: python

    def classify(value):
        if value < 0:
            return "negative"
        if value == 0:
            return "zero"
        return "positive"

Then analyze it from the command line:

.. code-block:: console

    $ cronenberg cc example.py -s
    example.py
        F 1:0 classify - A (3)

The ``cc`` command computes Cyclomatic Complexity. The ``-s`` flag includes
the numeric complexity score alongside its A–F rank.

Actually it's even better: it's got colors!

.. image:: https://cloud.githubusercontent.com/assets/238549/3707477/5793aeaa-1435-11e4-98fb-00e0bd8137f5.png
    :alt: A screen of Radon's cc command


**Note about file encoding**

On some systems, such as Windows, the default encoding is not UTF-8. If you are
using Unicode characters in your Python file and want to analyze it with Radon,
you'll have to set the `RADONFILESENCODING` environment variable to `UTF-8`.


On a Continuous Integration server
----------------------------------

If you are looking to use `radon` on a CI server you may be better off with
`xenon <https://github.com/rubik/xenon>`_. Although still experimental, it will
fail (that means exiting with a non-zero exit code) when various thresholds are
surpassed. `radon` is more of a reporting tool, while `xenon` is a monitoring
one.

If you are looking for more complete solutions, read the following sections.

Codacy
++++++++++++

`Codacy <https://www.codacy.com/>`_ uses Radon `by default <https://support.codacy.com/hc/en-us/articles/213632009-Engines#other-tools>`_ to calculate metrics from the source code.

Code Climate
++++++++++++

Radon is available as a `Code Climate Engine <https://docs.codeclimate.com/docs/list-of-engines>`_.
To understand how to add Radon's checks to your Code Climate Platform, head
over to their documentation:
https://docs.codeclimate.com/v1.0/docs/radon

coala Analyzer
++++++++++++++

Radon is also supported in `coala <http://coala.io/>`_. To add Radon's
checks to coala, simply add the ``RadonBear`` to one of the sections in
your ``.coafile``.

CodeFactor
++++++++++++

`CodeFactor <https://www.codefactor.io/>`_ uses Radon `out-of-the-box <https://support.codefactor.io/i24-analysis-tools-open-source>`_ to calculate Cyclomatic Complexity.

Links
-----

* Documentation: https://radon.readthedocs.org
* PyPI: http://pypi.python.org/pypi/radon
* Issue Tracker: https://github.com/rubik/radon/issues
