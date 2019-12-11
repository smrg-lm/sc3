import re


### Option 1 ###

_rewrite_symbols = {
    # Valid OSC address symbols with re meaning BEFORE special symbols rewrite.
    '(': '\(',
    ')': '\)',
    '^': '\^',
    '.': '\.',
    '$': '\$',
    '+': '\+',
    '|': '\|',
    '\\': '\\\\',

    # OSC special symbols (are invalid or special OSC Address symbols).
    '{': '(?:',
    ',': '|',
    '}': ')',
    '*': '.*',  # BUG: # lo ignora el * si luego viene ?, [, { o literal, por ejemplo: '/*bc'.matchOSCAddressPattern('/abc') es false y re.match('.bc', 'abc') devuelve match. Está en el párrafo anterior al cuadro en la especificación, dice que cada caracter de pattern debe coincidir con el próximo substring de address Y que todo caracter en address debe ser emparejado con algo de pattern.
    # '[': '[',  # Same.
    # '-': '-',  # Same behaviour inside/outside brackets.
    '[!': '[^',
    # ']': ']',  # Same.
    '-]': ']', # Discard '-' before closing bracket.
    '?': '.'
}


_rewrite_pattern = re.compile(
    '(' + '|'.join(re.escape(x) for x in _rewrite_symbols.keys()) + ')')


def _rewrite_func(match):
    return _rewrite_symbols[match.group(0)]


def osc_rematch_pattern(pattern, address):
    pattern = re.sub(_rewrite_pattern, _rewrite_func, pattern)
    return re.match(pattern, address) is not None


### Option 2 ###

def osc_match_pattern(pattern, address):
    # Based on liblo lo_pattern_match in PyrSymbolPrim.cpp.
    # Iterators and sets are used because it was easier not faster.
    # Should be faster then osc_rematch_pattern with cython and indexes,
    # may have some pattern definition issues from original.
    pattern = iter(pattern)
    address = iter(address)
    p = a = None

    negate = False
    prev_p = None
    char_set = None

    p_string = None
    a_string = None
    string_set = None

    try:
        while True:
            p = next(pattern, None)

            while p == '*':
                while p == '*':  # solo para quitar los '*' consecutivos.
                    p = next(pattern, None)

                if p is None:  # '*' es el último caracter, todo lo que quede en a vale.
                    return True

                if p != '?' and p != '[' and p != '{':  # '*?', '*[abc]', '*{a|b}' leaves '*' without effect.
                    a = next(address, None)
                    while a is not None and a != p:
                        a = next(address, None)

                    p = next(pattern, None)

            if p == '?':
                a = next(address, None)
                if a is None:
                    return False
            elif p == '[':
                char_set = set()
                p = next(pattern)  # StopIteration, pattern mal formado.

                if p == '!':
                    negate = True
                    p = next(pattern)  # StopIteration, pattern mal formado.
                else:
                    negate = False

                while p != ']':
                    prev_p = p  # necesita mirar antes
                    p = next(pattern)  # StopIteration, pattern mal formado.
                    if p == '-':
                        # el guión se puede descartar.
                        p = next(pattern)  # StopIteration, pattern mal formado.
                        if p != ']':
                            # es rango
                            char_set.update(
                                chr(x) for x in range(ord(prev_p), ord(p) + 1))
                        else:
                            char_set.add(prev_p)  # es fin de corchete, el guión de más no importa.
                    else:
                        char_set.add(prev_p)
                        char_set.add(p)

                a = next(address, None)
                if a is None:
                    return False

                if negate and a in char_set:
                    return False
                elif not negate and a not in char_set:
                    return False
            elif p == '{':
                string_set = set()
                p_string = ''
                a_string = ''

                while p != '}':
                    p = next(pattern)  # StopIteration, pattern mal formado.
                    if p == ',':
                        string_set.add(p_string)
                        p_string = ''
                    elif p == '}':
                        string_set.add(p_string)
                        break
                    else:
                        p_string += p

                a = next(address, None)
                while a != '/' and a is not None:
                    a_string += a
                    if a_string in string_set:
                        break
                    a = next(address, None)

                if a == '/' or a is None:
                    return False
            else:
                a = next(address, None)
                if p != a:
                    return False

                if p is None and a is None:
                    return True
    except StopIteration:
        # pattern mal formado en algunos casos
        return False
