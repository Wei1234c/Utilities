import os
import sys

from array import array


try:
    machine_name = os.uname().machine
except Exception:
    machine_name = os.name

IS_PC = machine_name.startswith('x86_64') or machine_name.startswith('nt')
IS_RPi = machine_name.startswith('armv')
IS_MICROPYTHON = (sys.implementation.name == 'micropython')

try:
    from bridges.ftdi.controllers.gpio import GpioController
    from bridges.ftdi.adapters.micropython.machine import Pin as ftdi_Pin
    from utilities.shift_register import ShiftRegister


    GPIO_PORT = GpioController()
except Exception as e:
    if not isinstance(e, ImportError):
        print(e)

try:
    from utilities.shift_register import ShiftRegister
except:
    from shift_register import ShiftRegister

VIRTUAL_DEVICE_WARNING = '\n****** Virtual device. Data may not be real ! ******\n'



class Mock:
    pass



class Pin:

    @classmethod
    def get_uPy_pin(cls, pin_id, output = True):
        import machine

        pin = machine.Pin(pin_id, machine.Pin.OUT if output else machine.Pin.IN)
        new_pin = Mock()

        if output:
            new_pin.low = lambda: pin.value(0)
            new_pin.high = lambda: pin.value(1)
        else:
            new_pin.value = pin.value

        return new_pin


    @classmethod
    def get_RPi_pin(cls, pin_id, output = True):
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)

        GPIO.setup(pin_id, GPIO.OUT if output else GPIO.IN)
        new_pin = Mock()

        if output:
            new_pin.low = lambda: GPIO.output(pin_id, GPIO.LOW)
            new_pin.high = lambda: GPIO.output(pin_id, GPIO.HIGH)
        else:
            new_pin.value = lambda: GPIO.input(pin_id)

        return new_pin


    @classmethod
    def get_Ftdi_pin(cls, pin_id, output = True):
        return ftdi_Pin(pin_id, mode = ftdi_Pin.OUT if output else ftdi_Pin.IN, gpio_port = GPIO_PORT)



class Bus:
    DEBUG_MODE = False


    def __init__(self, bus):
        self._bus = bus

        if self.is_virtual_device:
            print(VIRTUAL_DEVICE_WARNING)
        else:
            self.init()


    def init(self):
        if IS_RPi:
            raise NotImplementedError()
        elif IS_MICROPYTHON:
            raise NotImplementedError()
        elif IS_PC:
            raise NotImplementedError()


    @property
    def is_virtual_device(self):
        return self._bus is None


    def write(self, bytes_array):
        raise NotImplementedError()


    def read(self, n_bytes):
        raise NotImplementedError()



class SPI(Bus):
    SPI_MSB = 0
    SPI_LSB = 1


    def __init__(self, spi, ss, ss_polarity = 1):
        self._ss = ss
        self._ss_polarity = ss_polarity
        super().__init__(bus = spi)


    def init(self):
        if IS_RPi:
            self._write = self._bus.writebytes
        elif IS_MICROPYTHON or IS_PC:
            self._write = self._bus.write


    def write(self, bytes_array):

        if not self.is_virtual_device:

            if self._ss_polarity == 0:
                self._ss.low()
            self._ss.high()
            self._ss.low()

            result = self._write(bytes_array)

            self._ss.high()
            if self._ss_polarity == 0:
                self._ss.low()

            return result


    @classmethod
    def get_uPy_spi(cls, id = -1, baudrate = 10000000, polarity = 0, phase = 0, bits = 8, firstbit = SPI_MSB,
                    pin_id_sck = 14, pin_id_mosi = 13, pin_id_miso = 12):
        import machine

        spi = machine.SPI(id, baudrate = baudrate, polarity = polarity, phase = phase, bits = bits, firstbit = firstbit,
                          sck = machine.Pin(pin_id_sck, machine.Pin.OUT,
                                            machine.Pin.PULL_UP if polarity else machine.Pin.PULL_DOWN),
                          mosi = machine.Pin(pin_id_mosi, machine.Pin.OUT),  # , machine.Pin.PULL_UP),
                          miso = machine.Pin(pin_id_miso, machine.Pin.IN))  # , machine.Pin.PULL_UP))
        spi.init()

        return spi


    @classmethod
    def get_RPi_spi(cls, mode = 0b00, lsbfirst = False):
        import spidev

        spi = None

        try:
            spi = spidev.SpiDev()
            bus = 0
            device = 0
            spi.open(bus, device)
            spi.max_speed_hz = 10000000
            spi.mode = mode
            spi.lsbfirst = lsbfirst

        except Exception as e:
            print(e)

        return spi


    @classmethod
    def get_Ftdi_spi(cls, stb_pin, clk_pin, data_pin,
                     bits = ShiftRegister.BITS_IN_BYTE, lsbfirst = False,
                     polarity = ShiftRegister.POLARITY_DEFAULT, phase = ShiftRegister.PHASE_DEFAULT):

        return ShiftRegister(stb_pin = stb_pin, clk_pin = clk_pin, data_pin = data_pin, bits = bits,
                             lsbfirst = lsbfirst,
                             polarity = polarity, phase = phase)



class I2C(Bus):

    def __init__(self, i2c):
        super().__init__(bus = i2c)


    def init(self):
        if IS_RPi:

            self._read_addressed_byte = \
                lambda i2c_address, reg_address: self._bus.read_byte_data(i2c_address, reg_address)
            self._write_addressed_byte = \
                lambda i2c_address, reg_address, value: self._bus.write_byte_data(i2c_address, reg_address, value)

            # not sure how to implement read_bytes / write_bytes on RPi.

        elif IS_MICROPYTHON or IS_PC:
            self._read_addressed_byte = \
                lambda i2c_address, reg_address: self._bus.readfrom_mem(i2c_address, reg_address, 1)[0]
            self._write_addressed_byte = \
                lambda i2c_address, reg_address, value: self._bus.writeto_mem(i2c_address, reg_address,
                                                                              array('B', [value]))

            self._read_bytes = lambda i2c_address, n_bytes: self._bus.readfrom(i2c_address, n_bytes)
            self._write_bytes = lambda i2c_address, bytes_array: self._bus.writeto(i2c_address, bytes_array)


    def read_bytes(self, i2c_address, n_bytes):
        if not self.is_virtual_device:
            return self._read_bytes(i2c_address, n_bytes)
        return array('B', [0] * n_bytes)


    def read_byte(self, i2c_address):
        return self.read_bytes(i2c_address = i2c_address, n_bytes = 1)[0]


    def read_addressed_bytes(self, i2c_address, reg_address, n_bytes):
        if not self.is_virtual_device:
            self.write_byte(i2c_address = i2c_address, value = reg_address)
            return self.read_bytes(i2c_address = i2c_address, n_bytes = n_bytes)

        return array('B', [0] * n_bytes)


    def read_addressed_byte(self, i2c_address, reg_address):
        if not self.is_virtual_device:
            return self._read_addressed_byte(i2c_address, reg_address)
        return 0


    def write_bytes(self, i2c_address, bytes_array):
        if not self.is_virtual_device:
            return self._write_bytes(i2c_address, bytes_array)


    def write_byte(self, i2c_address, value):
        return self.write_bytes(i2c_address = i2c_address, bytes_array = array('B', [value]))


    def write_addressed_bytes(self, i2c_address, reg_address, bytes_array):
        n_bytes = len(bytes_array)

        if not self.is_virtual_device:
            ba = array('B', [reg_address])
            ba.extend(bytes_array)
            self.write_bytes(i2c_address = i2c_address, bytes_array = ba)

        return n_bytes


    def write_addressed_byte(self, i2c_address, reg_address, value):
        if not self.is_virtual_device:
            return self._write_addressed_byte(i2c_address, reg_address, value)


    @classmethod
    def get_uPy_i2c(cls, id = -1, scl_pin_id = 5, sda_pin_id = 4, freq = 400000):
        import machine

        return machine.I2C(scl = machine.Pin(scl_pin_id, machine.Pin.OUT),
                           sda = machine.Pin(sda_pin_id),
                           freq = freq)


    @classmethod
    def get_RPi_i2c(cls, bus_id = 1):
        from smbus2 import SMBus

        return SMBus(bus_id)


    @classmethod
    def get_Ftdi_i2c(cls):
        from bridges.ftdi.controllers.i2c import I2cController

        return I2cController().I2C(freq = 400000)
