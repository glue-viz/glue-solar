.. _developers_guide:

=================
Developer's Guide
=================

How to Contribute to Glue-viz
-----------------------------
There are three ways by which anyone can contribute to the ``Glue-viz`` package and the ``Glue-solar``
plugin in particular is not only code, but also to report any issues you have
encountered while using the software, helping to add or improve documentation, and to review a
pull request (PR). All these will benefit other users of solar physics as they use ``Glue-viz`` for
data visualization tasks, and help with the development of the community by offering them a valuable,
powerful, and open-source tool to facilitate their research. Details about these routes of contributing
are described below:

Reporting Issues
^^^^^^^^^^^^^^^^
If you use ``Glue`` with the ``Glue-viz`` plugin and encounter any problems, the best way to report it is
by opening an issue on our GitHub issue tracker. This way, we can help you work around the problem
and hopefully resolve it as soon as it arises. To use GitHub, you will will need to have a GitHub account
and be signed into it to report an issue. Having joined GitHub will make it easier to report and track
the issues you are a part of in the near future.

When reporting an issue, do try to provide a short description of what is at issue. For example, where possible
provide a small code sample for us to attempt to reproduce the error. Also, record any error output generated
when you stumbled upon the issue, so we can use this information to patch the codebase.

If there is functionality that is not currently available in ``Glue-viz`` or ``Glue-solar`` you can make
a feature request. Please provide as much information as possible regarding the feature you would like to see in
``Glue-solar``.

Documentation
^^^^^^^^^^^^^
``Glue-solar`` has some `online documentation <https://glue-solar.readthedocs.io/en/latest/>`__ and we strive to make it as comprehensive
as possible. This documentation contains the API of ``Glue-solar`` but also a user's guide
and developer documentation.

However, it is important to bear in mind that any documentation for any project is a living document.
It is never fully complete and there are always areas that could be expanded upon or would need further proofreading
to check for readability and easy comprehension. If some parts of the documentation are confusing or difficult
to follow, we would love to receive suggestions for improvements via issues or pull requests.

Reviewing a Pull Request
^^^^^^^^^^^^^^^^^^^^^^^^
At any moment in time we have a variety of pull requests opened, and getting them properly reviewed is important.
Generally speaking, it would be conducive to a higher standard for the patch if more people can look over
any particular pull request, as the better it will turn out with more people reviewing from different perspectives.
Therefore, we encourage everyone and anyone with varying levels of open-source development experience to do so.

Code Contributions
^^^^^^^^^^^^^^^^^^
If code contributions are preferred instead, the best way to start is to work on an existing or known issues.
Either the ``Glue-viz`` or ``Glue`` repositories are good staring points to investigate. The primary one is the
``Glue-viz`` repository with where all the known issues for the core package are detailed. Each issue
should have a series of labels that provide some information regarding its nature. If you find an issue
that you would like to work on, please make sure to add a comment to let people know that you are working on it.
This will ensure that it is less likely similar effort is duplicated by multiple parties.

In addition, you can also explore the repository of the ``Glue-solar`` plugin where you are encouraged to find
open issues there, and you might find these more interesting than those in the main ``Glue-viz`` repository.

Coding Standards
----------------
The purpose of this statement is to set forth the standards that are expected of all code contributions to
``Glue-solar``. All potential developers should read and abide by the following standards as much as possible.
Code which does not follow these standards closely will not be accepted.

Language Standard
^^^^^^^^^^^^^^^^^
1. All code must be compatible with Python 3.7 and later. Usage of ``six``, ``__future__``, and ``2to3``
is not acceptable.
2. The new Python 3 formatting style should be used throughout; i.e., use ``"{0:s}".format("spam")``
instead of ``"%s" % "spam"``.
3. The ``Glue`` package and the ``Glue-solar`` plugin should be importable with no dependencies other than those
already in ``Glue`` and ``Glue-solar``, the
`Python Standard Library <https://docs.python.org/3/library/index.html>`__, and packages that are already
requirements of both ``Glue`` and ``Glue-solar``. Adding extra dependencies to the mix could work under
special circumstances, but its practice is highly discouraged. Such optional dependencies should be recorded
in the ``setup.cfg`` file under ``extras_require``.

Coding Style / Conventions
^^^^^^^^^^^^^^^^^^^^^^^^^^
1. The code should follow the standard PEP8 Style Guide for Python Code. In particular, this includes
using only 4 spaces for indentation, but never tabs.
2. **Follow the existing coding style** within a file and avoid making changes that are purely stylistic.
Please try to maintain the style when adding or modifying code.
3. Following PEP8’s recommendation, absolute imports are to be used in general. Relative imports within a module are
allowed to avoid circular import chains.
4. The ``import numpy as np``, ``import matplotlib as mpl``, and ``import matplotlib.pyplot as plt`` naming conventions
for import statements should be used wherever and whenever relevant. However, ``from packagename import *`` should
never be used, expect in ``__init__.py``.
5. Classes should either use direct variable access, or Python’s property mechanism for setting
object instance variables.
6. Classes should use the builtin `super() <https://docs.python.org/3/library/functions.html#super>`__ function
when making calls to methods in their super-class(es), unless there are specific reasons not to. Also,
`super() <https://docs.python.org/3/library/functions.html#super>`__ should be used consistently in all subclasses,
since it does not work otherwise.
7. Multiple inheritance should be avoided in general without good justification.
8. The ``__init__.py`` files for each module should not contain any significant implementation code.
Each ``__init__.py`` can contain docstrings and code for organizing the module layout.

Documentation and Testing
^^^^^^^^^^^^^^^^^^^^^^^^^
1. American English is the default language for all documentation strings and inline commands.
Variables names should also be based on English words as far as possible.
2. Documentation strings must be present for all public classes/methods/functions. Furthermore, inclusion of
examples or tutorials in the package documentation is strongly recommended and encouraged.
3. Write usage examples in the docstrings of all classes and functions whenever possible.
These examples should be short and simple to reproduce, so that users would be able to copy them verbatim
and run them. These examples should also, whenever possible, be in the
`doctest <https://docs.astropy.org/en/stable/development/testguide.html#doctests>`__
format and will be executed as part of the test suite.
4. Unit tests should be provided for as many public methods and functions as possible.

Glue-solar Documentation Rules
------------------------------
We recommend following for example the
`SunPy Documentation Rules <https://docs.sunpy.org/en/latest/dev_guide/documentation.html>`__, though it is not
required to follow the rules strictly as we prefer to use these as guidelines rather than rules.

Overview
^^^^^^^^
For the RST files, we recommend a one-sentence-per-line rule and ignore the line length.

Sphinx
^^^^^^
All of the ``Glue-solar`` documentation (like this page) is built with
`Sphinx <https://www.sphinx-doc.org/en/stable/>`__, which is a tool very suitable for documenting Python projects.
Sphinx works by parsing files written in a
`Media-wiki-like syntax <http://docutils.sourceforge.net/docs/user/rst/quickstart.html>`__ called
`reStructuredText <http://docutils.sourceforge.net/rst.html>`__. In addition to parsing static files
of reStructuredText, Sphinx can be instructed to parse code comments as well. In fact, in addition
to what you are reading right now, the `Python documentation <https://www.python.org/doc/>`__
has also created using Sphinx.

All of the ``Glue-solar`` documentation is contained in the “docs” folder and code documentation strings.

To build the docs with tox, in the root directory run::

    tox -e build_docs

This command will generate HTML documentation for ``Glue-solar`` in your local "docs/_build/html" directory.
You can then open the "index.html" file to browse the final docs build.

Testing Guidelines
------------------

Testing Frameworks
^^^^^^^^^^^^^^^^^^
The testing framework used in ``Glue-solar`` are the ``pytest`` and ``tox`` frameworks.

Using pytest to run tests
^^^^^^^^^^^^^^^^^^^^^^^^^
The test suite can be run directly from the native ``pytest`` command. In this case, it is important
or developers to be aware that they must manually rebuild any extensions by running ``python setup.py build_ext``
before testing.

At the root of the repository directory, to run the entire suite with pytest::

    pytest

will use the settings in the ``setup.cfg`` file.

If you only want to run one specific test file, use a command similar to the following::

    pytest glue_solar/tests/test_pixel_extraction.py

or if you only want one specific test in the test file::

    pytest glue_solar/tests/test_pixel_extraction.py::<test_name>

If a test yields errors, you can use pdb to create a debugging session at the moment the test fails::

    pytest --pdb

Using tox to run tests
^^^^^^^^^^^^^^^^^^^^^^
Another method to run tests locally is to use ``tox``, which is a generic virtualenv management and testing
command line tool. We have several environments within our ``tox.ini`` file and you can list them using the below::

    tox -l

Then you can run the tests in any of these doing::

    tox -e <name_of_env>

This will create a test environment in “.tox” and build, install ``Glue-Solar`` and runs the entire test suite.
This is the method that our continuous integration (CI) uses. Please note that individual unit tests can only be run
on its own with ``pytest``, with ``tox`` the entire test suite is run per invocation of the command.

Basic Glue Concepts
-------------------
For a thorough treatment of the concepts used in ``Glue``, we recommend going through the official
documentation specifically for writing custom viewers, which is a three-part series, to be found at
`Writing a custom viewer for glue <http://docs.glueviz.org/en/latest/customizing_guide/viewer.html>`__,
`Writing a custom viewer for glue with Qt <http://docs.glueviz.org/en/latest/customizing_guide/qt_viewer.html>`__
as well as `Writing a custom viewer for glue with Qt and
Matplotlib <http://docs.glueviz.org/en/latest/customizing_guide/matplotlib_qt_viewer.html>`__,
in detail in the order stated, as the series progresses in difficulty accordingly. Broadly speaking, to be
a proficient ``Glue`` developer, you will need to familiarize themselves with the notions of state classes,
the layer artist, and the data viewer. These are indispensable parts for a custom viewer, which is important
for developing your own tailored solar physics visualization solutions apart from the tools we provide with the
``Glue-solar`` plugin. Also, to add support for alternate data formats, you will need to have the concept of a
data factory, which is based on the native data structures of ``Glue``.
