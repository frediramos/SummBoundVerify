import subprocess as sp


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

    def compile(self):
        gcc_cmd = [
            'gcc',
            *self.gcc_args,
            self.inputfile,
            '-o', self.outputfile,
            *self.libs
        ]

        print(' '.join(gcc_cmd))

        t = sp.Popen(gcc_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        stdout, stderr = t.communicate()
        out = stdout.decode()
        err = stderr.decode()

        print(out, end='')
        print(err, end='')
