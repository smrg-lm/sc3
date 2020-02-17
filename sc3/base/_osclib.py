"""
The content of this file is a modified version of python-osc from

https://github.com/attwad/python-osc

whose License is as follows:

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
"""


import struct
import socketserver
import sys
import logging
import collections
from typing import Union, Tuple, Any, Iterator, List

from . import main as _libsc3


_logger = logging.getLogger(__name__)


### OSC Exceptions ###


class OscParseError(Exception):
    pass


class OscTypeParseError(OscParseError):
    pass


class OscMessageParseError(OscParseError):
    pass


class OscBundleParseError(OscParseError):
    pass


class OscBuildError(Exception):
    pass


class OscTypeBuildError(OscBuildError):
    pass


class OscMessageBuildError(OscBuildError):
    pass


class OscBundleBuildError(OscBuildError):
    pass


### Constants ###


IMMEDIATELY = 1

_IMMEDIATELY_DGRAM = struct.pack('>Q', 1)
_BUNDLE_PREFIX_DGRAM = b'#bundle\x00'
_EMPTY_STR_DGRAM = b'\x00\x00\x00\x00'

_INT_DGRAM_LEN = 4
_FLOAT_DGRAM_LEN = 4
_DOUBLE_DGRAM_LEN = 8
_TIMETAG_DGRAM_LEN = 8

# Strings and blob dgram length is always a multiple of 4 bytes.
_STRING_DGRAM_PAD = 4
_BLOB_DGRAM_PAD = 4


### OSC Types ###


def write_string(val: str) -> bytes:
    """Returns the OSC string equivalent of the given python string.

    Raises:
      - BuildError if the string could not be encoded.
    """
    try:
        dgram = val.encode('utf-8')  # Default, but better be explicit.
    except (UnicodeEncodeError, AttributeError) as e:
        raise OscTypeBuildError('Incorrect string, could not encode') from e
    diff = _STRING_DGRAM_PAD - (len(dgram) % _STRING_DGRAM_PAD)
    dgram += (b'\x00' * diff)
    return dgram


def get_string(dgram: bytes, start_index: int) -> Tuple[str, int]:
    """Get a python string from the datagram, starting at pos start_index.

    According to the specifications, a string is:
    "A sequence of non-null ASCII characters followed by a null,
    followed by 0-3 additional null characters to make the total number
    of bits a multiple of 32".

    Args:
      dgram: A datagram packet.
      start_index: An index where the string starts in the datagram.

    Returns:
      A tuple containing the string and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    if start_index < 0:
        raise OscTypeParseError('start_index < 0')
    offset = 0
    try:
        if (len(dgram) > start_index + _STRING_DGRAM_PAD
                and dgram[start_index + _STRING_DGRAM_PAD] == _EMPTY_STR_DGRAM):
            return '', start_index + _STRING_DGRAM_PAD
        while dgram[start_index + offset] != 0:
            offset += 1
        # Align to a byte word.
        if (offset) % _STRING_DGRAM_PAD == 0:
            offset += _STRING_DGRAM_PAD
        else:
            offset += (-offset % _STRING_DGRAM_PAD)
        # Python slices do not raise an IndexError past the last index,
        # do it ourselves.
        if offset > len(dgram[start_index:]):
            raise OscTypeParseError('Datagram is too short')
        data_str = dgram[start_index:start_index + offset]
        return data_str.replace(b'\x00', b'').decode('utf-8'), start_index + offset
    except IndexError as e:
        raise OscTypeParseError('Could not parse datagram') from e
    except TypeError as e:
        raise OscTypeParseError('Could not parse datagram') from e


def write_int(val: int) -> bytes:
    """Returns the datagram for the given integer parameter value

    Raises:
      - BuildError if the int could not be converted.
    """
    try:
        return struct.pack('>i', val)
    except struct.error as e:
        raise OscTypeBuildError('Wrong argument value passed') from e


def get_int(dgram: bytes, start_index: int) -> Tuple[int, int]:
    """Get a 32-bit big-endian two's complement integer from the datagram.

    Args:
      dgram: A datagram packet.
      start_index: An index where the integer starts in the datagram.

    Returns:
      A tuple containing the integer and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _INT_DGRAM_LEN:
            raise OscTypeParseError('Datagram is too short')
        return (
            struct.unpack(
                '>i', dgram[start_index:start_index + _INT_DGRAM_LEN])[0],
            start_index + _INT_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise OscTypeParseError('Could not parse datagram') from e


def write_timetag(timetag: int) -> bytes:
    try:
        return struct.pack('>Q', timetag)
    except struct.error as e:
        raise OscTypeBuildError('Wrong argument value passed') from e


def get_timetag(dgram: bytes, start_index: int) -> Tuple[int, int]:
    """Get a 64-bit big-endian unsigned integer from the datagram.

    Args:
      dgram: A datagram packet.
      start_index: An index where the integer starts in the datagram.

    Returns:
      Time as unsigned int OSC timetag.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _TIMETAG_DGRAM_LEN:
            raise OscTypeParseError('Datagram is too short')
        return (
            struct.unpack(
                '>Q', dgram[start_index:start_index + _TIMETAG_DGRAM_LEN])[0],
            start_index + _TIMETAG_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise OscTypeParseError('Could not parse datagram') from e


def write_float(val: float) -> bytes:
    """Returns the datagram for the given float parameter value

    Raises:
      - BuildError if the float could not be converted.
    """
    try:
        return struct.pack('>f', val)
    except struct.error as e:
        raise OscTypeBuildError('Wrong argument value passed') from e


def get_float(dgram: bytes, start_index: int) -> Tuple[float, int]:
    """Get a 32-bit big-endian IEEE 754 floating point number from the datagram.

    Args:
      dgram: A datagram packet.
      start_index: An index where the float starts in the datagram.

    Returns:
      A tuple containing the float and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _FLOAT_DGRAM_LEN:
            # Noticed that Reaktor doesn't send the last bunch of \x00 needed to make
            # the float representation complete in some cases, thus we pad here to
            # account for that.
            dgram = dgram + b'\x00' * (_FLOAT_DGRAM_LEN - len(dgram[start_index:]))
        return (
            struct.unpack(
                '>f', dgram[start_index:start_index + _FLOAT_DGRAM_LEN])[0],
            start_index + _FLOAT_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise OscTypeParseError('Could not parse datagram') from e


def write_double(val: float) -> bytes:
    """Returns the datagram for the given double parameter value

    Raises:
      - BuildError if the double could not be converted.
    """
    try:
        return struct.pack('>d', val)
    except struct.error as e:
        raise OscTypeBuildError('Wrong argument value passed') from e


def get_double(dgram: bytes, start_index: int) -> Tuple[float, int]:
    """Get a 64-bit big-endian IEEE 754 floating point number from the datagram.

    Args:
      dgram: A datagram packet.
      start_index: An index where the double starts in the datagram.

    Returns:
      A tuple containing the double and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _DOUBLE_DGRAM_LEN:
            raise ParseError('Datagram is too short')
        return (
            struct.unpack(
                '>d', dgram[start_index:start_index + _DOUBLE_DGRAM_LEN])[0],
            start_index + _DOUBLE_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise OscTypeParseError('Could not parse datagram') from e


def write_blob(val: bytes) -> bytes:
    """Returns the datagram for the given blob parameter value.

    Raises:
      - BuildError if the value was empty or if its size didn't fit an OSC int.
    """
    if not val:
        raise OscTypeBuildError('Blob value cannot be empty')
    dgram = write_int(len(val))
    dgram += val
    while len(dgram) % _BLOB_DGRAM_PAD != 0:
        dgram += b'\x00'
    return dgram


def get_blob(dgram: bytes, start_index: int) -> Tuple[bytes, int]:
    """ Get a blob from the datagram.

    According to the specifications, a blob is made of
    "an int32 size count, followed by that many 8-bit bytes of arbitrary
    binary data, followed by 0-3 additional zero bytes to make the total
    number of bits a multiple of 32".

    Args:
      dgram: A datagram packet.
      start_index: An index where the float starts in the datagram.

    Returns:
      A tuple containing the blob and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    size, int_offset = get_int(dgram, start_index)
    # Make the size a multiple of 32 bits.
    total_size = size + (-size % _BLOB_DGRAM_PAD)
    end_index = int_offset + size
    if end_index - start_index > len(dgram[start_index:]):
        raise OscTypeParseError('Datagram is too short')
    return dgram[int_offset:int_offset + size], int_offset + total_size


def write_rgba(val: bytes) -> bytes:
    """Returns the datagram for the given rgba32 parameter value

    Raises:
      - BuildError if the int could not be converted.
    """
    try:
        return struct.pack('>I', val)
    except struct.error as e:
        raise OscTypeBuildError('Wrong argument value passed') from e


def get_rgba(dgram: bytes, start_index: int) -> Tuple[bytes, int]:
    """Get an rgba32 integer from the datagram.

    Args:
      dgram: A datagram packet.
      start_index: An index where the integer starts in the datagram.

    Returns:
      A tuple containing the integer and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _INT_DGRAM_LEN:
            raise OscTypeParseError('Datagram is too short')
        return (
            struct.unpack(
                '>I', dgram[start_index:start_index + _INT_DGRAM_LEN])[0],
            start_index + _INT_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise OscTypeParseError('Could not parse datagram') from e


def write_midi(val: Tuple[Tuple[int, int, int, int], int]) -> bytes:
    """Returns the datagram for the given MIDI message parameter value

       A valid MIDI message: (port id, status byte, data1, data2).

    Raises:
      - BuildError if the MIDI message could not be converted.
    """
    if len(val) != 4:
        raise OscTypeBuildError('MIDI message length is invalid')
    try:
        value = sum(
            (value & 0xFF) << 8 * (3 - pos) for pos, value in enumerate(val))
        return struct.pack('>I', value)
    except struct.error as e:
        raise OscTypeBuildError('Wrong argument value passed') from e


def get_midi(dgram: bytes, start_index: int) -> Tuple[Tuple[int, int, int, int], int]:
    """Get a MIDI message (port id, status byte, data1, data2) from the datagram.

    Args:
      dgram: A datagram packet.
      start_index: An index where the MIDI message starts in the datagram.

    Returns:
      A tuple containing the MIDI message and the new end index.

    Raises:
      ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _INT_DGRAM_LEN:
            raise OscTypeParseError('Datagram is too short')
        val = struct.unpack(
            '>I', dgram[start_index:start_index + _INT_DGRAM_LEN])[0]
        midi_msg = tuple(
            (val & 0xFF << 8 * i) >> 8 * i for i in range(3, -1, -1))
        return (midi_msg, start_index + _INT_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise OscTypeParseError('Could not parse datagram') from e


### OSC Bundle ###


class OscBundle(object):
    """Bundles elements that should be triggered at the same time.

    An element can be another OscBundle or an OscMessage.
    """

    def __init__(self, dgram: bytes):
        """Initializes the OscBundle with the given datagram.

        Args:
          dgram: a UDP datagram representing an OscBundle.
        Raises:
          ParseError: if the datagram could not be parsed into an OscBundle.
        """
        # Interesting stuff starts after the initial b"#bundle\x00".
        self._dgram = dgram
        index = len(_BUNDLE_PREFIX_DGRAM)
        try:
            self._timetag, index = get_timetag(self._dgram, index)
        except OscTypeParseError as e:
            raise OscBundleParseError(
                'Could not get the timetag from datagram') from e
        # Get the contents as a list of OscBundle and OscMessage.
        self._contents = self._parse_contents(index)

    # Return type is actually List[OscBundle], but that would require import annotations from __future__, which is
    # python 3.7+ only.
    def _parse_contents(self, index: int) -> Any:
        contents = []
        try:
            # An OSC Bundle Element consists of its size and its contents.
            # The size is an int32 representing the number of 8-bit bytes in the
            # contents, and will always be a multiple of 4. The contents are either
            # an OSC Message or an OSC Bundle.
            while self._dgram[index:]:
                # Get the sub content size.
                content_size, index = get_int(self._dgram, index)
                # Get the datagram for the sub content.
                content_dgram = self._dgram[index:index + content_size]
                # Increment our position index up to the next possible content.
                index += content_size
                # Parse the content into an OSC message or bundle.
                if OscBundle.dgram_is_bundle(content_dgram):
                    contents.append(OscBundle(content_dgram))
                elif OscMessage.dgram_is_message(content_dgram):
                    contents.append(OscMessage(content_dgram))
                else:
                    _logger.warning('Could not identify content type '
                                    f'of dgram {content_dgram}')
        except (OscTypeParseError, OscMessageParseError, IndexError) as e:
            raise OscBundleParseError(
                "Could not parse a content datagram") from e

        return contents

    @staticmethod
    def dgram_is_bundle(dgram: bytes) -> bool:
        """Returns whether this datagram starts like an OSC bundle."""
        return dgram.startswith(_BUNDLE_PREFIX_DGRAM)

    @property
    def timetag(self) -> int:
        """Returns the timetag associated with this bundle."""
        return self._timetag

    @property
    def num_contents(self) -> int:
        """Shortcut for len(*bundle) returning the number of elements."""
        return len(self._contents)

    @property
    def size(self) -> int:
        """Returns the length of the datagram for this bundle."""
        return len(self._dgram)

    @property
    def dgram(self) -> bytes:
        """Returns the datagram from which this bundle was built."""
        return self._dgram

    def content(self, index) -> Any:
        """Returns the bundle's content 0-indexed."""
        return self._contents[index]

    def __iter__(self) -> Iterator[Any]:
        """Returns an iterator over the bundle's content."""
        return iter(self._contents)


### OSC Bundle Builder ###


class OscBundleBuilder(object):
    """Builds arbitrary OscBundle instances."""

    def __init__(self, timetag: int):
        """
        Build a new bundle with the associated timetag as uint64.
        """
        self._timetag = timetag
        self._contents = []

    def add_content(self, content):
        """Add a new content to this bundle.

        Args:
          - content: Either an OscBundle or an OscMessage
        """
        self._contents.append(content)

    def build(self):
        """Build an OscBundle with the current state of this builder.

        Raises:
          - BuildError: if we could not build the bundle.
        """
        dgram = _BUNDLE_PREFIX_DGRAM
        try:
            dgram += write_timetag(self._timetag)
            for content in self._contents:
                if type(content) is OscMessage or type(content) is OscBundle:
                    size = content.size
                    dgram += write_int(size)
                    dgram += content.dgram
                else:
                    raise OscBundleBuildError(
                        'Content must be either OscBundle or OscMessage '
                        f'found {type(content).__name__}')
            return OscBundle(dgram)
        except OscTypeBuildError as e:
            raise OscBundleBuildError('Could not build the bundle') from e


### OSC Message ###


class OscMessage(object):
    """Representation of a parsed datagram representing an OSC message.

    An OSC message consists of an OSC Address Pattern followed by an OSC
    Type Tag String followed by zero or more OSC Arguments.
    """

    def __init__(self, dgram: bytes) -> None:
        self._dgram = dgram
        self._parameters = []
        self._parse_datagram()

    def _parse_datagram(self) -> None:
        try:
            self._address_regexp, index = get_string(self._dgram, 0)
            if not self._dgram[index:]:
                # No params is legit, just return now.
                return

            # Get the parameters types.
            type_tag, index = get_string(self._dgram, index)
            if type_tag.startswith(','):
                type_tag = type_tag[1:]

            params = []
            param_stack = [params]
            # Parse each parameter given its type.
            for param in type_tag:
                if param == "i":  # Integer.
                    val, index = get_int(self._dgram, index)
                elif param == "f":  # Float.
                    val, index = get_float(self._dgram, index)
                elif param == "d":  # Double.
                    val, index = get_double(self._dgram, index)
                elif param == "s":  # String.
                    val, index = get_string(self._dgram, index)
                elif param == "b":  # Blob.
                    val, index = get_blob(self._dgram, index)
                elif param == "r":  # RGBA.
                    val, index = get_rgba(self._dgram, index)
                elif param == "m":  # MIDI.
                    val, index = get_midi(self._dgram, index)
                elif param == "t":  # osc time tag:
                    val, index = get_timetag(self._dgram, index)
                elif param == "T":  # True.
                    val = True
                elif param == "F":  # False.
                    val = False
                elif param == "[":  # Array start.
                    array = []
                    param_stack[-1].append(array)
                    param_stack.append(array)
                elif param == "]":  # Array stop.
                    if len(param_stack) < 2:
                        raise OscMessageParseError(
                            'Unexpected closing bracket '
                            f'in type tag: {type_tag}')
                    param_stack.pop()
                # TODO: Support more exotic types as described in the specification.
                else:
                    _logger.warning(f'Unhandled parameter type: {param}')
                    continue
                if param not in "[]":
                    param_stack[-1].append(val)
            if len(param_stack) != 1:
                raise OscMessageParseError(
                    f'Missing closing bracket in type tag: {type_tag}')
            self._parameters = params
        except OscTypeParseError as e:
            raise OscMessageParseError(
                'Found incorrect datagram, ignoring it') from e

    @property
    def address(self) -> str:
        """Returns the OSC address regular expression."""
        return self._address_regexp

    @staticmethod
    def dgram_is_message(dgram: bytes) -> bool:
        """Returns whether this datagram starts as an OSC message."""
        return dgram.startswith(b'/')

    @property
    def size(self) -> int:
        """Returns the length of the datagram for this message."""
        return len(self._dgram)

    @property
    def dgram(self) -> bytes:
        """Returns the datagram from which this message was built."""
        return self._dgram

    @property
    def params(self) -> List[Any]:
        """Convenience method for list(self) to get the list of parameters."""
        return list(self)

    def __iter__(self) -> Iterator[float]:
        """Returns an iterator over the parameters of this message."""
        return iter(self._parameters)


### OSC Message Builder ###


class OscMessageBuilder(object):
    """Builds arbitrary OscMessage instances."""

    ARG_TYPE_FLOAT = "f"
    ARG_TYPE_DOUBLE = "d"
    ARG_TYPE_INT = "i"
    ARG_TYPE_STRING = "s"
    ARG_TYPE_BLOB = "b"
    ARG_TYPE_RGBA = "r"
    ARG_TYPE_MIDI = "m"
    ARG_TYPE_TRUE = "T"
    ARG_TYPE_FALSE = "F"
    ARG_TYPE_NIL = "N"

    ARG_TYPE_ARRAY_START = "["
    ARG_TYPE_ARRAY_STOP = "]"

    _SUPPORTED_ARG_TYPES = (
        ARG_TYPE_FLOAT, ARG_TYPE_DOUBLE, ARG_TYPE_INT, ARG_TYPE_BLOB,
        ARG_TYPE_STRING, ARG_TYPE_RGBA, ARG_TYPE_MIDI, ARG_TYPE_TRUE,
        ARG_TYPE_FALSE, ARG_TYPE_NIL)

    def __init__(self, address: str=None) -> None:
        """Initialize a new builder for a message.

        Args:
          - address: The osc address to send this message to.
        """
        self._address = address
        self._args = []

    @property
    def address(self) -> str:
        """Returns the OSC address this message will be sent to."""
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        """Sets the OSC address this message will be sent to."""
        self._address = value

    @property
    def args(self) -> List[Tuple[str, Union[str, bytes, bool, int, float, tuple, list]]]:   # TODO: Make 'tuple' more specific for it is a MIDI packet
        """Returns the (type, value) arguments list of this message."""
        return self._args

    def _valid_type(self, arg_type: str) -> bool:
        if arg_type in self._SUPPORTED_ARG_TYPES:
            return True
        elif isinstance(arg_type, list):
            for sub_type in arg_type:
                if not self._valid_type(sub_type):
                    return False
            return True
        return False

    def add_arg(self, arg_value: Union[str, bytes, bool, int, float, tuple, list], arg_type: str=None) -> None:     # TODO: Make 'tuple' more specific for it is a MIDI packet
        """Add a typed argument to this message.

        Args:
          - arg_value: The corresponding value for the argument.
          - arg_type: A value in ARG_TYPE_* defined in this class,
                      if none then the type will be guessed.
        Raises:
          - ValueError: if the type is not supported.
        """
        if arg_type and not self._valid_type(arg_type):
            raise ValueError(
                f'arg_type must be one of {self._SUPPORTED_ARG_TYPES}, '
                'or an array of valid types')
        if not arg_type:
            arg_type = self._get_arg_type(arg_value)
        if isinstance(arg_type, list):
            self._args.append((self.ARG_TYPE_ARRAY_START, None))
            for v, t in zip(arg_value, arg_type):
                self.add_arg(v, t)
            self._args.append((self.ARG_TYPE_ARRAY_STOP, None))
        else:
            self._args.append((arg_type, arg_value))

    def _get_arg_type(self, arg_value: Union[str, bytes, bool, int, float, tuple, list]) -> str:    # TODO: Make 'tuple' more specific for it is a MIDI packet
        """Guess the type of a value.

        Args:
          - arg_value: The value to guess the type of.
        Raises:
          - ValueError: if the type is not supported.
        """
        if isinstance(arg_value, str):
            arg_type = self.ARG_TYPE_STRING
        elif isinstance(arg_value, (bytes, bytearray, memoryview)):
            arg_type = self.ARG_TYPE_BLOB
        elif arg_value is True:
            arg_type = self.ARG_TYPE_TRUE
        elif arg_value is False:
            arg_type = self.ARG_TYPE_FALSE
        elif isinstance(arg_value, int):
            arg_type = self.ARG_TYPE_INT
        elif isinstance(arg_value, float):
            arg_type = self.ARG_TYPE_FLOAT
        elif isinstance(arg_value, tuple) and len(arg_value) == 4:
            arg_type = self.ARG_TYPE_MIDI
        elif isinstance(arg_value, list):  # NOTE: not a valid case from sc3.
            arg_type = [self._get_arg_type(v) for v in arg_value]
        elif arg_value is None:
            arg_type = self.ARG_TYPE_NIL
        else:
            raise ValueError(
                f'Infered arg_value type is not supported: {type(arg_value)}')
        return arg_type

    def build(self):
        """
        Builds an OscMessage from the current state of this builder.

        Raises:
          - BuildError: if the message could not be build or if the address
            was empty.
        Returns:
          - an OscMessage instance.
        """
        if not self._address:
            raise OscMessageBuildError('OSC addresses cannot be empty')
        dgram = b''
        try:
            # Write the address.
            dgram += write_string(self._address)
            if not self._args:
                dgram += write_string(',')
                return OscMessage(dgram)

            # Write the parameters.
            arg_types = "".join([arg[0] for arg in self._args])
            dgram += write_string(',' + arg_types)
            for arg_type, value in self._args:
                if arg_type == self.ARG_TYPE_STRING:
                    dgram += write_string(value)
                elif arg_type == self.ARG_TYPE_INT:
                    dgram += write_int(value)
                elif arg_type == self.ARG_TYPE_FLOAT:
                    dgram += write_float(value)
                elif arg_type == self.ARG_TYPE_DOUBLE:
                    dgram += write_double(value)
                elif arg_type == self.ARG_TYPE_BLOB:
                    dgram += write_blob(value)
                elif arg_type == self.ARG_TYPE_RGBA:
                    dgram += write_rgba(value)
                elif arg_type == self.ARG_TYPE_MIDI:
                    dgram += write_midi(value)
                elif arg_type in (self.ARG_TYPE_TRUE,
                                  self.ARG_TYPE_FALSE,
                                  self.ARG_TYPE_ARRAY_START,
                                  self.ARG_TYPE_ARRAY_STOP,
                                  self.ARG_TYPE_NIL):
                    continue
                else:
                    raise OscMessageBuildError(
                        f'Incorrect parameter type found {arg_type}')

            return OscMessage(dgram)
        except OscTypeBuildError as e:
            raise OscMessageBuildError(f'Could not build the message') from e


### OSC Packet ###


TimedMessage = collections.namedtuple(
    typename='TimedMessage',
    field_names=('time', 'message'))


class OscPacket():
    def __init__(self, dgram: bytes):
        if OscBundle.dgram_is_bundle(dgram):
            self._messages = self._get_bundle_messages(OscBundle(dgram))
            self._messages = sorted(self._messages, key=lambda x: x.time or 0)
        elif OscMessage.dgram_is_message(dgram):
            self._messages = [TimedMessage(None, OscMessage(dgram))]
        else:
            # Empty packet (because UDP).
            raise OscParseError('OSC packet should at least contain '
                                'an OscMessage or OscBundle')  # *** BUG: ver si un msj con solo address vale

    @property
    def messages(self):
        return self._messages

    def _get_bundle_messages(self, bundle):
        messages = []
        for content in bundle:
            if type(content) is OscMessage:
                messages.append(TimedMessage(bundle.timetag, content))
            else:
                messages.extend(self._get_bundle_messages(content))
        return messages


### OSC Server ###


class UDPHandler(socketserver.BaseRequestHandler):
    def handle(self):  # override
        packet = OscPacket(self.request[0])
        for timed_msg in packet.messages:
            msg = [timed_msg.message.address, *timed_msg.message.params]
            _libsc3.main._osc_interface.recv(
                self.client_address, timed_msg.time, *msg)
        # NOTE: Exception are handled by BaseServer.handle_error, "The default action is to print the traceback to standard error and continue handling further requests."
        # NOTE: "The type of self.request is different for datagram or stream services. For stream services, self.request is a socket object; for datagram services, self.request is a pair of string and socket."


class OSCUDPServer(socketserver.UDPServer):
    def verify_request(self, request, client_address):  # override
        return (OscBundle.dgram_is_bundle(request[0]) or
                OscMessage.dgram_is_message(request[0]))

    def handle_error(self, request, client_address):  # override
        _logger.error(
            'Exception happened during processing '
            f'request from {client_address}',
            exc_info=sys.exc_info())


# class ThreadingOSCUDPServer(socketserver.ThreadingMixIn, OSCUDPServer):
#     pass
