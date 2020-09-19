"""
R/W functions for SynthDef format.
"""

import struct


def read_pascal_str(stream):  # getPascalString
    str_len = struct.unpack('B', stream.read(1))[0]
    return str(stream.read(str_len), 'ascii')

def read_i8(stream):  # getInt8
    return struct.unpack('b', stream.read(1))[0]

def read_i16(stream):  # getInt16
    return struct.unpack('>h', stream.read(2))[0]

def read_i32(stream):  # getInt32
    return struct.unpack('>i', stream.read(4))[0]

def read_i8_list(stream, n):  # read Int8Array
    data = stream.read(n)
    return list(struct.unpack('b' * n, data))

def read_i32_list(stream, n):  # read Int32Array
    data = stream.read(n * 4)
    return list(struct.unpack('>' + 'i' * n, data))

def read_f32_list(stream, n):  # read FloatArray
    data = stream.read(n * 4)
    return list(struct.unpack('>' + 'f' * n, data))


def write_pascal_str(stream, string):  # putPascalString
    stream.write(struct.pack('B', len(string)))  # unsigned int8 -> bytes
    stream.write(bytes(string, 'ascii'))

def write_i8(stream, value):  # putInt8
    stream.write(struct.pack('b', value))

def write_i16(stream, value):  # putInt16
    stream.write(struct.pack('>h', value))

def write_i32(stream, value):  # putInt32
    stream.write(struct.pack('>i', value))

def write_f32(stream, value):  # putFloat
    stream.write(struct.pack('>f', value))
