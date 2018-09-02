# -*- coding: utf-8 -*-
"""Test backwards compatibility modules using separate subprocesses."""
import subprocess
import sys

from datatest._compatibility import textwrap
from . import _unittest as unittest


class TestBackwardsCompatibility(unittest.TestCase):
    def assertSubprocess(self, module):
        """Run given *module* in separate process--fails if return code
        indicates an error.
        """
        command = [sys.executable, '-B', '-O', '-m', module]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = p.communicate()  # Closes file-like object.

        # A non-zero return code indicates the command was not successful.
        if p.returncode != 0:
            output = stdout_bytes + stderr_bytes      # Get all output.
            output = output.decode('utf-8')           # Convert bytes to str.
            output = textwrap.wrap(output, width=70)  # Get list of wrapped lines.
            output = '\n'.join(output)                # Join list items as str.
            output = textwrap.indent(output, '    ')  # Indent lines by 4 spaces.

            msg = '\n'.join([
                'Subprocess failed:',
                output,
                '',
                'To run this test directly, use the following command:',
                ' '.join(command),
            ])
            self.fail(msg)

    def test_api00(self):
        """Test compatibility with pre-release alpha API."""
        self.assertSubprocess('tests.past_api00')

    def test_api06(self):
        """Test compatibility with first development-release API."""
        self.assertSubprocess('tests.past_api06')

    def test_api07(self):
        """Test compatibility with second development-release API."""
        self.assertSubprocess('tests.past_api07')

    def test_api08(self):
        """Test compatibility with version 0.8 API."""
        self.assertSubprocess('tests.past_api08')


if __name__ == '__main__':
    unittest.main()
