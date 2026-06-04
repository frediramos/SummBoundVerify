import logging
import subprocess as sp

from pathlib import Path
from typing import Literal

from summboundverify.exceptions import CompilationError

Arch = Literal['x86', 'x64']

logger = logging.getLogger(__name__)


class CCompiler():
    def __init__(
        self,
        arch: Arch,
        inputfile: str | Path,
        outputfile: str | Path,
        libs: list[str]
    ):

        self.arch = arch
        self.inputfile = Path(inputfile)
        self.outputfile = Path(outputfile)

        self.gcc_args = [
            '-Wall', '-O0',
            '-Wno-implicit-function-declaration',
            '-Wno-int-conversion',
            '-Wno-unused-variable',
            '-fno-builtin'
        ]

        if self.arch == 'x86':
            self.gcc_args.append('-m32')

        self.libs = libs or []

    def compile(self, verbose=True):
        cmd = [
            'gcc',
            *self.gcc_args,
            str(self.inputfile),
            '-o', (self.outputfile),
            *self.libs
        ]

        cmd_string = ' '.join(cmd)

        result = sp.run(cmd, capture_output=True, text=True)
        out = result.stdout
        err = result.stderr

        if result.returncode != 0:
            raise CompilationError(err, cmd_string)

        if verbose:
            self.log(cmd_string, out, err)

    def log(self, cmd: str, out: str, err: str):
        logger.info(f"Compiling:\n {cmd}")
        if out:
            logger.info(out)
        if err:
            logger.warning(err)
