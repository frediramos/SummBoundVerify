import logging
import subprocess as sp


logger = logging.getLogger(__name__)


class CCompiler():
    def __init__(self, arch, inputfile, outputfile, libs):

        self.arch = arch
        self.inputfile = inputfile
        self.outputfile = self.binary_name(outputfile)

        self.gcc_args = ['-Wall', '-O0',
                         '-Wno-implicit-function-declaration',
                         '-Wno-int-conversion',
                         '-Wno-unused-variable',
                         '-fno-builtin']

        if self.arch == 'x86':
            self.gcc_args.append('-m32')

        if not libs:
            libs = []
        self.libs = libs

    def binary_name(self, file):
        if file[-2:] == '.c':
            return file[:-2]
        return file

    def compile(self, verbose=True):
        cmd = [
            'gcc',
            *self.gcc_args,
            self.inputfile,
            '-o', self.outputfile,
            *self.libs
        ]

        t = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        stdout, stderr = t.communicate()
        out = stdout.decode()
        err = stderr.decode()

        if verbose:
            self.log(cmd, out, err)

    def log(self, cmd, out, err):
        cmd = ' '.join(cmd)
        logger.info(f"Compiling:\n {cmd}")
        if out:
            logger.info(out)
        if err:
            logger.warning(err)
