# Signed values are converted with two's compliment.
from math import ceil



class Number:

    # https://en.wikipedia.org/wiki/Single-precision_floating-point_format

    def __init__(self, value):
        self.value = value


    @classmethod
    def from_bits(cls, bits):
        raise NotImplementedError


    @classmethod
    def from_bytes(cls, value_bytes):
        raise NotImplementedError


    @classmethod
    def bits_to_value(cls, bits):
        raise NotImplementedError


    @classmethod
    def bytes_to_value(cls, value_bytes):
        raise NotImplementedError


    @classmethod
    def to_bits(cls, value):
        raise NotImplementedError


    @classmethod
    def to_bytes(cls, value):
        raise NotImplementedError


    @property
    def bits(self):
        return self.to_bits(self.value)


    @property
    def bytes(self):
        return self.to_bytes(self.value)



class SignedInteger(Number):
    N_BITS = 32


    def __init__(self, value, n_bits = None):
        super().__init__(value)
        self._n_bits = n_bits or self.N_BITS

        self.limit_guard(value, self._n_bits)


    @classmethod
    def limit_guard(cls, value, n_bits):
        limit = 1 << (n_bits - 1)
        assert - limit <= value < limit, f'Need {-limit} <= value < {limit}, current: {value}'


    @classmethod
    def from_bits(cls, bits, n_bits):
        return cls(cls.bits_to_value(bits, n_bits), n_bits)


    @classmethod
    def from_bytes(cls, value_bytes, n_bits):
        return cls(cls.bytes_to_value(value_bytes, n_bits), n_bits)


    @classmethod
    def bits_to_value(cls, bits, n_bits):
        sign_mask = 1 << (n_bits - 1)
        return (bits & (sign_mask - 1)) - \
               (bits & (sign_mask - 0))


    @classmethod
    def bytes_to_value(cls, value_bytes, n_bits):
        bits = int.from_bytes(value_bytes, byteorder = 'big', signed = False)
        return cls.bits_to_value(bits, n_bits)


    @classmethod
    def to_bits(cls, value, n_bits):
        return value + 2 ** n_bits if value < 0 else value


    @classmethod
    def to_bytes(cls, value, n_bits):
        bits = cls.to_bits(value, n_bits)
        return bits.to_bytes(length = ceil(n_bits / 8),
                             byteorder = 'big',
                             signed = False)


    @property
    def bits(self):
        return self.to_bits(self.value, self._n_bits)


    @property
    def bytes(self):
        return self.to_bytes(self.value, self._n_bits)



class Float(Number):
    # https://en.wikipedia.org/wiki/Single-precision_floating-point_format
    # https://docs.python.org/3/library/struct.html

    N_BITS_A = 9
    N_BITS_B = 23


    def __init__(self, value, n_bits_A = None, n_bits_B = None):
        super().__init__(value)
        self._n_bits_A = n_bits_A or self.N_BITS_A
        self._n_bits_B = n_bits_B or self.N_BITS_B

        SignedInteger.limit_guard(value, self._n_bits_A)


    @classmethod
    def from_bits(cls, bits, n_bits_A = None, n_bits_B = None):
        n_bits_A = n_bits_A or cls.N_BITS_A
        n_bits_B = n_bits_B or cls.N_BITS_B
        return cls(cls.bits_to_value(bits, n_bits_A, n_bits_B), n_bits_A, n_bits_B)


    @classmethod
    def from_bytes(cls, AB_bytes, n_bits_A = None, n_bits_B = None):
        n_bits_A = n_bits_A or cls.N_BITS_A
        n_bits_B = n_bits_B or cls.N_BITS_B
        return cls(cls.bytes_to_value(AB_bytes, n_bits_A, n_bits_B), n_bits_A, n_bits_B)


    @classmethod
    def bits_to_value(cls, bits, n_bits_A, n_bits_B):
        denominator = 1 << n_bits_B
        return SignedInteger.bits_to_value(bits, n_bits_A + n_bits_B) / denominator


    @classmethod
    def bytes_to_value(cls, AB_bytes, n_bits_A, n_bits_B):
        bits = int.from_bytes(AB_bytes, byteorder = 'big', signed = False)
        return cls.bits_to_value(bits, n_bits_A, n_bits_B)


    @classmethod
    def to_bits(cls, value, n_bits_A, n_bits_B):
        SignedInteger.limit_guard(value, n_bits_A)

        denominator = 1 << n_bits_B
        numerator = int(value * denominator)

        return SignedInteger.to_bits(numerator, n_bits_A + n_bits_B)


    @classmethod
    def to_bytes(cls, value, n_bits_A, n_bits_B):
        bits = cls.to_bits(value, n_bits_A, n_bits_B)
        return bits.to_bytes(length = ceil((n_bits_A + n_bits_B) / 8),
                             byteorder = 'big',
                             signed = False)


    @property
    def bits(self):
        return self.to_bits(self.value, self._n_bits_A, self._n_bits_B)


    @property
    def bytes(self):
        return self.to_bytes(self.value, self._n_bits_A, self._n_bits_B)


