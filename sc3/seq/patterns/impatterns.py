"""From Patterns.sc"""


from .. import pattern as ptt


### Imperative patterns ###


class Ptime(ptt.Pattern):
    # // Returns relative time (in beats) from moment of embedding.
    ...


# // if an error is thrown in the stream, func is evaluated
# class Pprotect(FilterPattern): # BUG: FilterPatterns.sc
#     ...


class Pif(ptt.Pattern):
    ...
