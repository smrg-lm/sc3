"""
Herramientas para detectar los imports cíclicos,
podría elaborar para que sea algo más completo y
automático, podría ser que ya haya alguna librería así.
"""


imp_data = {
    '_global': [],
    '_specialindex': [],
    'builtins': ['functions'],
    'clock': ['main', 'thread', 'builtins'],
    'engine': ['builtins'],
    'functions': ['builtins'],
    'inout': ['ugens', '_global', 'utils'],
    'line': ['ugens'],
    'main': ['server', 'clock', 'thread', 'oscserver', 'responsedefs'],
    'model': [],
    'netaddr': ['main'],
    'node': ['utils', 'ugens', 'server', 'synthdesc'],
    'osc': ['ugens'],
    'oscserver': ['utils', 'netaddr', 'main', 'clock'],
    'platform': [],
    'responsedefs': ['systemactions', 'model', 'main', 'utils'],
    'server': ['main', 'utils', 'netaddr', 'model', 'engine', 'synthdef', 'clock', 'systemactions', 'serverstatus', 'responsedefs', 'thread'],
    'serverstatus': ['clock', 'model', 'thread', 'systemactions', 'responsedefs'],
    'stream': ['functions'],
    'synthdef': ['inout', '_global', 'utils', 'ugens', 'systemactions', 'server', 'platform', 'synthdesc'],
    'synthdesc': ['_global', 'inout', 'utils', 'ugens', 'server', 'systemactions', 'synthdef'],
    'systemactions': [],
    'thread': ['clock', 'main', 'stream'],
    'ugens': ['functions', '_global', 'utils'], #, 'node'], # BUG: no puede importar node, ver ugens
    'utils': []
}


def show_path(module, imports=imp_data, print_rec=True):
    print(module + ':', imports[module])
    def _(module, imports, prevmodules, path, level):
        dashes = '|   ' * level
        for submod in imports[module]:
            if submod in prevmodules:
                if print_rec:
                    if submod in path:
                        # La cantidad de asteríscos muestra si es cíclico
                        # inmediátamente (1) o a través de la cadena
                        # de imports (2 o más). Se necesita saber si estuvo
                        # en un path anterior también?
                        recl = '*' * (len(path) - path.index(submod) - 1)
                        print(dashes + recl + submod)
                    else:
                        # Estuvo en un path anterior pero no en el actual.
                        print(dashes + '+' + submod)
                continue
            else:
                print(dashes[:len(dashes) - 1], submod)
                level += 1
                prevmodules.add(submod)
                path.append(submod)
                _(submod, imports, prevmodules, path, level)
                level -= 1
                path.remove(submod)
    _(module, imports, set([module]), [module], 1)


def show_cyclic(imports=imp_data):
    registered = set()
    for mod in imports:
        for submod in imports[mod]:
            if mod in imports[submod]:
                reg1 = (mod, submod)
                reg2 = (submod, mod)
                if reg1 not in registered\
                and reg2 not in registered:
                    registered.add(reg1)
                    print(mod, '<->', submod)
    return registered
