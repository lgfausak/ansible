# (c) 2014, Chris Church <chris@ninemoreminutes.com>
#
# This file is part of Ansible.
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


from ansible.module_utils.six.moves import shlex_quote
from ansible.plugins.shell import ShellBase


class ShellModule(ShellBase):

    # Common shell filenames that this plugin handles.
    # Note: sh is the default shell plugin so this plugin may also be selected
    # if the filename is not listed in any Shell plugin.
    COMPATIBLE_SHELLS = frozenset(('sh', 'zsh', 'bash', 'dash', 'ksh'))
    # Family of shells this has.  Must match the filename without extension
    SHELL_FAMILY = 'sh'

    # How to end lines in a python script one-liner
    _SHELL_EMBEDDED_PY_EOL = '\n'
    _SHELL_REDIRECT_ALLNULL = '> /dev/null 2>&1'
    _SHELL_AND = '&&'
    _SHELL_OR = '||'
    _SHELL_SUB_LEFT = '"`'
    _SHELL_SUB_RIGHT = '`"'
    _SHELL_GROUP_LEFT = '('
    _SHELL_GROUP_RIGHT = ')'

    def checksum(self, path, python_interp):
        # The following test needs to be SH-compliant.  BASH-isms will
        # not work if /bin/sh points to a non-BASH shell.
        #
        # In the following test, each condition is a check and logical
        # comparison (|| or &&) that sets the rc value.  Every check is run so
        # the last check in the series to fail will be the rc that is
        # returned.
        #
        # If a check fails we error before invoking the hash functions because
        # hash functions may successfully take the hash of a directory on BSDs
        # (UFS filesystem?) which is not what the rest of the ansible code
        # expects
        #
        # If all of the available hashing methods fail we fail with an rc of
        # 0.  This logic is added to the end of the cmd at the bottom of this
        # function.

        # Return codes:
        # checksum: success!
        # 0: Unknown error
        # 1: Remote file does not exist
        # 2: No read permissions on the file
        # 3: File is a directory
        # 4: No python interpreter

        # Quoting gets complex here.  We're writing a python string that's
        # used by a variety of shells on the remote host to invoke a python
        # "one-liner".
        shell_escaped_path = shlex_quote(path)
        test = "rc=flag; [ -r %(p)s ] %(shell_or)s rc=2; [ -f %(p)s ] %(shell_or)s rc=1; [ -d %(p)s ] %(shell_and)s rc=3; %(i)s -V 2>/dev/null %(shell_or)s rc=4; [ x\"$rc\" != \"xflag\" ] %(shell_and)s echo \"${rc}  \"%(p)s %(shell_and)s exit 0" % dict(p=shell_escaped_path, i=python_interp, shell_and=self._SHELL_AND, shell_or=self._SHELL_OR)  # NOQA
        csums = [
            u"({0} -c 'import hashlib; BLOCKSIZE = 65536; hasher = hashlib.sha1();{2}afile = open(\"'{1}'\", \"rb\"){2}buf = afile.read(BLOCKSIZE){2}while len(buf) > 0:{2}\thasher.update(buf){2}\tbuf = afile.read(BLOCKSIZE){2}afile.close(){2}print(hasher.hexdigest())' 2>/dev/null)".format(python_interp, shell_escaped_path, self._SHELL_EMBEDDED_PY_EOL),  # NOQA  Python > 2.4 (including python3)
            u"({0} -c 'import sha; BLOCKSIZE = 65536; hasher = sha.sha();{2}afile = open(\"'{1}'\", \"rb\"){2}buf = afile.read(BLOCKSIZE){2}while len(buf) > 0:{2}\thasher.update(buf){2}\tbuf = afile.read(BLOCKSIZE){2}afile.close(){2}print(hasher.hexdigest())' 2>/dev/null)".format(python_interp, shell_escaped_path, self._SHELL_EMBEDDED_PY_EOL),  # NOQA  Python == 2.4
        ]

        cmd = (" %s " % self._SHELL_OR).join(csums)
        cmd = "%s; %s %s (echo \'0  \'%s)" % (test, cmd, self._SHELL_OR, shell_escaped_path)
        return cmd
