import subprocess as sp
import re


def write2file(file, var):
    with open(file, 'a') as f:
        f.write(f'{var}\n')


def truncate(file):
    with open(file, 'w'):
        return


def get_states(sm):
    states = sm.deadended + sm.active
    return states


def get_fnames(binary):

    def clean_addr(addr):
        addr = re.sub(r'^0+', '', addr)
        return addr

    symbols = {}

    # nm binary | grep \ T \
    command_nm = ['nm', binary]
    command_grep = ['grep', '\\ T\\ ']

    p1 = sp.Popen(command_nm, stdout=sp.PIPE)
    p2 = sp.Popen(command_grep, stdin=p1.stdout, stdout=sp.PIPE)
    nm_out, _ = p2.communicate()
    nm_out = nm_out.decode('utf-8')

    for line in nm_out.splitlines():
        split = line.split()
        addr = split[0]
        symbol = split[2]
        symbols[clean_addr(addr)] = symbol

    # objdump -d binary | grep \ plt \
    command_objdump = ['objdump', '-d', binary]
    command_grep = ['grep', '@plt\\>']

    p3 = sp.Popen(command_objdump, stdout=sp.PIPE)
    p4 = sp.Popen(command_grep, stdin=p3.stdout, stdout=sp.PIPE)
    objdump_out, _ = p4.communicate()
    objdump_out = objdump_out.decode('utf-8')

    for line in objdump_out.splitlines():
        split = line.split()
        addr = split[-2]
        symbol = split[-1]
        symbol = re.split(r'[@ \< \>]', symbol)[1]
        symbols[clean_addr(addr)] = symbol

    return symbols
