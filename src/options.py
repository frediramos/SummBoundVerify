class OptionTypes:

    BOOL = 'boolean'
    SIMPLE = 'simple'
    LIST = 'list'
    NESTED = 'nested'
    DICT = 'dict'


class MetaOptions(type):

    def __values(self):
        return {k: v for k, v in vars(self).items() if '__' not in k}.values()

    def __keys(self):
        return [opt[1] for opt in self.__values()]

    def __iter__(self):
        for v in self.__values():
            yield v

    def __contains__(self, v):
        return v in self.__keys()

    def __len__(self):
        return len(self.__values())


class Options(metaclass=MetaOptions):

    # Validation Gen
    o = ('-', 'o', OptionTypes.SIMPLE)
    func = ('-', 'func', OptionTypes.SIMPLE)
    summ = ('-', 'summ', OptionTypes.SIMPLE)
    summname = ('--', 'summname', OptionTypes.SIMPLE)
    funcname = ('--', 'funcname', OptionTypes.SIMPLE)
    arraysize = ('--', 'arraysize', OptionTypes.NESTED)
    nullbytes = ('--', 'nullbytes', OptionTypes.NESTED)
    defaultvalues = ('--', 'defaultvalues', OptionTypes.NESTED)
    maxvalue = ('--', 'maxvalue', OptionTypes.LIST)
    maxnames = ('--', 'maxnames', OptionTypes.LIST)
    concretearray = ('--', 'concretearray', OptionTypes.DICT)
    lib = ('--', 'lib', OptionTypes.LIST)
    noapi = ('-', 'noapi', OptionTypes.BOOL)
    compile = ('--', 'compile', OptionTypes.SIMPLE)
    memory = ('-', 'memory', OptionTypes.BOOL)
    config = ('-', 'config', OptionTypes.SIMPLE)

    # Validation Run
    run = ('-', 'run', OptionTypes.BOOL)
    binary = ('--', 'binary', OptionTypes.SIMPLE)
    timeout = ('-', 'timeout', OptionTypes.SIMPLE)
    results = ('--', 'results', OptionTypes.SIMPLE)
    stats = ('--', 'stats', OptionTypes.SIMPLE)
    ascii = ('-', 'ascii', OptionTypes.BOOL)
    debug = ('-', 'debug', OptionTypes.BOOL)
