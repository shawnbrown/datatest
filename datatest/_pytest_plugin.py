# -*- coding: utf-8 -*-
"""
A pytest plugin for test driven data-wrangling with datatest.

IMPORTANT: Users of Datatest should only install ``datatest``
itself, not the ``pytest_datatest`` development package.

This plugin is bundled with the datatest however, it's developed
separately. This is done for a few reasons:

1. Datatest should work as expected out-of-the-box. The plugin
   code is small enough that including it does not impact the
   user experience for non-pytest users. Offering the plugin as
   an optional dependency would add a step to the installation
   process for no real benefit.
2. Following pytest's plugin submission guidelines seems like
   good practice for long-term maintenance. But the guidelines
   aren't easily implemented for datatest as a whole. Maintaining
   the plugin in a separate repository makes it easier to follow
   the guidelines without having to retool the main datatest
   project.
3. Datatest supports more versions of Python than does Pytest
   or tox. The separate repository provides a clean separation
   between the two sets of test requirements.

Developers of the Datatest project should install both
``datatest`` and ``pytest_datatest``. When both packages
are installed, ``pytest_datatest`` is used in place of
the bundled version.
"""

import itertools
import re
import warnings

import pytest
import _pytest  # Non-public API.
from datatest import ValidationError


def _warn_import_fallback(name):
    message = 'could not import {0}; using fallback'.format(name)
    warnings.warn(message, stacklevel=2)


try:
    from _pytest.assertion.truncate import _should_truncate_item
except ImportError:
    import os

    _warn_import_fallback('_should_truncate_item')

    def _should_truncate_item(item):  # Adapted from pytest 6.1.1.
        verbose = item.config.option.verbose
        return verbose < 2 and not _running_on_ci()

    def _running_on_ci():  # Adapted from pytest 6.1.1.
        env_vars = ['CI', 'BUILD_NUMBER']
        return any(var in os.environ for var in env_vars)


try:
    from _pytest.assertion.truncate import DEFAULT_MAX_LINES
except ImportError:
    _warn_import_fallback('DEFAULT_MAX_LINES')
    DEFAULT_MAX_LINES = 8  # Adapted from pytest 6.1.1.


try:
    from _pytest.assertion.truncate import DEFAULT_MAX_CHARS
except ImportError:
    _warn_import_fallback('DEFAULT_MAX_CHARS')
    DEFAULT_MAX_CHARS = 8 * 80  # Adapted from pytest 6.1.1.


try:
    from _pytest.assertion.truncate import USAGE_MSG
except ImportError:
    _warn_import_fallback('USAGE_MSG')
    USAGE_MSG = "use '-vv' to show"  # Adapted from pytest 6.1.1.


try:
    _fail_marker = _pytest._code.code.FormattedExcinfo.fail_marker
except AttributeError:
    warnings.warn('could not reference fail_marker; using fallback')
    _fail_marker = 'E'


if __name__ == 'pytest_datatest':
    from datatest._pytest_plugin import version_info as _bundled_version_info
else:
    _bundled_version_info = (0, 0, 0)


version = '0.1.4'
version_info = (0, 1, 4)

PYTEST54 = str(pytest.__version__[:3]) == '5.4'

_idconfig_session_dict = {}  # Dictionary to store ``session`` reference.


def pytest_addoption(parser):
    """Add the '--ignore-mandatory' command line option."""
    # The following try/except block is needed because this hook
    # runs before we have a chance to turn-off the bundled plugin,
    # so this option might have already been added.
    group = parser.getgroup('Datatest')
    try:
        group.addoption(
            '--ignore-mandatory',
            action='store_true',
            help=(
                "ignore 'mandatory' marker (continues testing "
                "even when a mandatory test fails)."
            ),
        )
    except ValueError as exc:
        if 'already added' not in str(exc):
            raise


def pytest_plugin_registered(plugin, manager):
    """If running the development version, turn-off the bundled plugin."""
    development_plugin = __name__ == 'pytest_datatest'
    if development_plugin:
        manager.set_blocked(name='datatest')  # Block bundled plugin.


def pytest_configure(config):
    """Register 'mandatory' marker."""
    config.addinivalue_line(
        'markers',
        'mandatory: test is mandatory, stops session early on failure.',
    )


def pytest_collection_modifyitems(session, config, items):
    """Store ``session`` reference to use in pytest_terminal_summary()."""
    global _idconfig_session_dict
    _idconfig_session_dict[id(config)] = session


# Compile regex pattern and get fail_marker.
_diff_start_regex = re.compile(
    r'^E\s+(?:datatest.)?ValidationError:.+\d+ difference[s]?.*: [\[{]$')


def _find_validationerror_position(lines):
    """Return the index position where a ValidationError begins in the
    given list of *lines*. Return -1 if no ValidationError is found.
    """
    for position, line in enumerate(lines):
        if line.startswith(_fail_marker):
            if _diff_start_regex.search(line) is not None:
                return position  # <- EXIT!
            break  # Stop after 1st fail_marker regardless of match.
    return -1


def _formatted_lines_generator(lines, position):
    """Return a generator of formatted *lines* that contain a
    ValidationError at the given *position*.

    The resulting lines will have an unqualified class name (simply
    "ValidationError") and the fail markers ("E") will be replaced
    with spaces.
    """
    lines = iter(lines)

    # Yield lines up to the given index position without changes.
    for line in itertools.islice(lines, 0, position):
        yield line

    # Yield first failure-line, removing "datatest." and keeping fail_marker.
    fail_line = next(lines)
    yield fail_line.replace('datatest.ValidationError', 'ValidationError', 1)

    # Yield subsequent failure-lines, replacing fail_marker with spaces.
    marker_length = len(_fail_marker)
    marker_spaces = ' ' * marker_length
    for line in lines:
        if line.startswith(_fail_marker):
            yield marker_spaces + line[marker_length:]  # <- Replaces fail_marker.
        else:
            yield line
            break  # Stop checking for fail_marker after first line without a fail_marker.

    # Yield any remaining lines without changes.
    for line in lines:
        yield line


if PYTEST54:
    class ReprEntry(_pytest._code.code.ReprEntry):
        """Custom ReprEntry--USE ONLY WITH PYTEST 5.4.X VERSIONS."""
        def __init__(self, reprentry):
            self.lines = reprentry.lines
            self.reprfuncargs = reprentry.reprfuncargs
            self.reprlocals = reprentry.reprlocals
            self.reprfileloc = reprentry.reprfileloc
            self.style = reprentry.style

        def _write_entry_lines(self, tw):
            """This method is adapted from Pytest version 6.1.1."""

            if not self.lines:
                return

            fail_marker = "{0}   ".format(
                _pytest._code.code.FormattedExcinfo.fail_marker)
            indent_size = len(fail_marker)
            indents = []
            source_lines = []
            failure_lines = []
            for index, line in enumerate(self.lines):
                is_failure_line = line.startswith(fail_marker)
                if is_failure_line:
                    # from this point on all lines are considered part of the failure
                    failure_lines.extend(self.lines[index:])
                    break
                else:
                    if self.style == "value":
                        source_lines.append(line)
                    else:
                        indents.append(line[:indent_size])
                        source_lines.append(line[indent_size:])

            tw._write_source(source_lines, indents)

            # failure lines are always completely red and bold
            for line in failure_lines:
                tw.line(line, bold=True, red=True)


def _format_reprtraceback(reprtraceback):
    for reprentry in reprtraceback.reprentries:
        try:
            lines = reprentry.lines
            position = _find_validationerror_position(lines)
            if position != -1:
                lines = _formatted_lines_generator(lines, position)
                reprentry.lines = list(lines)
        except AttributeError:
            # On pytest versions 3.3 through 3.6, sessions using `xdist`
            # return `dict` instances instead of ReprEntry instances.
            lines = reprentry['lines']
            position = _find_validationerror_position(lines)
            if position != -1:
                lines = _formatted_lines_generator(lines, position)
                reprentry['lines'] = list(lines)

    if PYTEST54:
        reprtraceback.reprentries = \
            [ReprEntry(entry) for entry in reprtraceback.reprentries]


def pytest_runtest_logreport(report):
    """Hook to format the ReprEntry lines for ValidationErrors"""

    if report.when != 'call' or report.longrepr is None:
        return

    longrepr = report.longrepr
    try:
        # Try `chain` attribute (assuming ExceptionChainRepr).
        for element_tuple in longrepr.chain:
            reprtraceback = element_tuple[0]
            _format_reprtraceback(reprtraceback)
    except AttributeError:
        try:
            # Try `reprtraceback` attribute (assuming ExceptionRepr).
            _format_reprtraceback(longrepr.reprtraceback)
        except AttributeError:
            # Unknown type goes unmodified.
            pass


def _should_truncate(line_count, char_count):
    return (line_count > DEFAULT_MAX_LINES) or (char_count > DEFAULT_MAX_CHARS)


_truncation_notice = '...Full output truncated, {0}'.format(USAGE_MSG)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook wrapper to replace ReprEntry instances for ValidationError
    exceptions and to handle failure of 'mandatory' tests.
    """
    if call.when == 'call':

        datafail = call.excinfo and call.excinfo.errisinstance(ValidationError)

        # Pytest-style truncation must be applied before `yield`.
        if datafail and _should_truncate_item(item):
            call.excinfo.value._should_truncate = _should_truncate
            call.excinfo.value._truncation_notice = _truncation_notice

        outcome = yield

        # If test was mandatory, session should fail immediately.
        if call.excinfo:
            try:
                mandatory = item.get_closest_marker('mandatory')
            except AttributeError:
                try:
                    mandatory = item.get_marker('mandatory')  # pytest <= 3.5
                except AttributeError:
                    mandatory = False  # in pytest <= 3.6 item can be non-Item

            if mandatory and not item.config.getoption('--ignore-mandatory'):
                shouldfail = 'mandatory {0!r} failed'.format(item.name)
                item.session.shouldfail = shouldfail

    else:
        outcome = yield  # noqa: F841 (set flake8 to ignore)


def pytest_terminal_summary(terminalreporter, exitstatus):
    """Add sections to terminal summary report when appropriate."""

    session = _idconfig_session_dict.get(id(terminalreporter.config), None)
    shouldfail = str(getattr(session, 'shouldfail', ''))
    if shouldfail.startswith('mandatory') and shouldfail.endswith('failed'):
        markup = {'yellow': True}
        terminalreporter.write_sep('_', **markup)
        terminalreporter.write(
            (
                "\n"
                "stopping early, {0}\n"
                "use '--ignore-mandatory' to continue testing\n"
                "\n"
            ).format(shouldfail),
            **markup
        )

    if _bundled_version_info > version_info:
        markup = {'yellow': True, 'bold': True}
        terminalreporter.section('NOTICE', **markup)
        terminalreporter.write(
            (
                "\n"
                "The installed version of the 'pytest_datatest' plugin "
                "is older than the bundled version included with datatest "
                "itself.\n"
                "\n"
                "Uninstall 'pytest_datatest' to automatically enable the "
                "newer version.\n"
                "\n"
            ),
            **markup
        )
