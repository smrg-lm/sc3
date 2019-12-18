
class _Dendrite():
    # Incomplete and not really usefull class
    # following MultiLevelIdentityDictionary.

    def __init__(self):
        self.dictionary = dict()

    def __getitem__(self, path):
        path_lst = self._as_path(path)
        last = path_lst.pop()
        sub = self.dictionary
        for key in path_lst:
            if key in sub:
                if isinstance(sub[key], dict):
                    sub = sub[key]
                else:
                    sub = dict()  # next key will fail if current wasn't last.
            else:
                raise KeyError(tuple(path))
        err = None
        try:
            return sub[last]
        except KeyError as e:
            err = e
        if err:
            raise KeyError(tuple(path))

    def _as_path(self, value):
        # TODO: o restringir a que sea solo una tupla
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, collections.Hashable):
            return [value]
        raise KeyError(f'{type(value).__name__} is not a valid path')

    def __setitem__(self, path, value):
        path_lst = self._as_path(path)
        last = path_lst.pop()
        sub = self.dictionary
        # prev_sub = sub
        # prev_key = None
        for key in path_lst:
            if isinstance(sub, dict):
                if key in sub:
                    # prev_sub = sub
                    # prev_key = key
                    sub = sub[key]
                else:
                    sub[key] = dict()
                    sub = sub[key]
            else:
                # TODO: que se puedan hacer forks en ambos casos, el nodo
                # TODO: contiene una list/tuple con el valor terminal (uno
                # TODO: solo) y un camino anidado, cambiarían get y contains.
                # prev_sub[prev_key] = dict()
                # sub = prev_sub[prev_key]
                # sub[key] = dict()
                # sub = sub[key]
                raise KeyError(
                    f'existing path fork before {key}: {tuple(path)}')
        if isinstance(sub, dict):
            sub[last] = value
        else:
            raise KeyError(f'leaf path fork at {last}: {tuple(path)}')

    def __delitem__(self, path):
        path_lst = self._as_path(path)
        last = path_lst.pop()
        sub = self.dictionary
        for key in path_lst:
            if key in sub:
                sub = sub[key]
            else:
                raise KeyError(tuple(path))
        del sub[last]

    def __contains__(self, path):
        path_lst = self._as_path(path)
        sub = self.dictionary
        for key in path_lst:
            if key in sub:
                if isinstance(sub[key], dict):
                    sub = sub[key]
                else:
                    sub = dict()  # next key will fail if current wasn't last.
            else:
                return False
        return True

    def __repr__(self):
        msg = type(self).__name__ + '('
        msg += self.dictionary.__repr__() + ')'
        return msg

    def __str__(self):
        sub = self.dictionary
        self._msg = ''
        self._make_str(sub, 0)
        return self._msg

    def _make_str(self, sub, level):
        for key in sub:
            if isinstance(sub[key], dict):
                self._msg += ('  ' * level) + str(key) + ': ' + '\n'
                self._make_str(sub[key], level + 1)
            else:
                self._msg += ('  ' * level) + str(key) + ': ' + str(sub[key]) + '\n'
