import random
import cocotb

from cocotb.triggers import Timer, RisingEdge, FallingEdge, Combine, Join, First
from cocotb.clock import Clock
from cocotb.result import TestFailure
from itertools import product
from random import randint

from collections import namedtuple


def int_to_bits(i, length):
    if i < 0:
        raise ValueError("Number mus be >= 0")
    return [int(x) for x in bin(i)[2:].zfill(length)]


class DiffLine:

    def __init__(self, p, n):
        self.p = p
        self.n = n

    def set(self, v):
        self.p <=  (v & 0x1)
        self.n <= ~(v & 0x1)

    def __le__(self, v):
        self.set(v)

    def __int__(self):
        return self.p.value.integer


class DiffSPIMaster:

    def __init__(self, dut, sck_pn, miso_pn, mosi_pn, csn_pn, sck_freq):
        self.sck = DiffLine(*sck_pn)
        self.miso = DiffLine(*miso_pn)
        self.mosi = DiffLine(*mosi_pn)
        self.csn = DiffLine(*csn_pn)

        self.sck <= 0
        self.mosi <= 0
        self.csn <= 0

        self.sck_period = 1e9/sck_freq
        
    @cocotb.coroutine
    def transfer(self, value, length):
        self.csn <= 1
        vals = int_to_bits(value, length)
        readout = []
        for v in vals:
            self.mosi <= v
            yield Timer(self.sck_period/2, 'ns')
            self.sck <= 1
            yield Timer(self.sck_period/2, 'ns')
            self.sck <= 0
            # readout.append(int(self.miso))
        self.csn <= 0
        yield Timer(self.sck_period*2, 'ns')
        return readout
   
   
# noinspection PyStatementEffect
class TbPhaser:

    def __init__(self, dut):
        self.dut = dut

        gp = lambda x: getattr(dut, x)

        self.spi = DiffSPIMaster(dut, 
            sck_pn=[gp("lvds_p"), gp("lvds_n")],
            miso_pn=[gp("lvds_p_2"), gp("lvds_n_2")],
            mosi_pn=[gp("lvds_p_1"), gp("lvds_n_1")],
            csn_pn=[gp("lvds_p_3"), gp("lvds_n_3")],
            sck_freq=125000000)

        cocotb.fork(self.clock())

    @cocotb.coroutine
    def clock(self):
        clk = DiffLine(self.dut.clk125_p, self.dut.clk125_n)       
        while True:
            clk <= 0
            yield Timer(4000)
            clk <= 1
            yield Timer(4000)

    def signal_array_to_value(self, A):
        v = 0
        for i, a in enumerate(reversed(A)):
            v |= a.value.integer << i
        return v

    @cocotb.coroutine
    def test_pattern_monitor(self, iface, rising_edge, pattern):
        play = self.dut.phaser_dac_play
        AB = [getattr(self.dut, "dac_d{}_p_{}".format(iface, i)) for i in reversed(range(1,16))]
        AB.append(getattr(self.dut, "dac_d{}_p".format(iface)))
        yield RisingEdge(play)
        print("Starting pattern monitor for pattern {}...".format(pattern))
        i = 0
        while True:
            if rising_edge:
                yield RisingEdge(self.dut.dac_dataclk_p)
            else:
                yield RisingEdge(self.dut.dac_dataclk_n)
            readout = self.signal_array_to_value(AB)
            expected = pattern[i % len(pattern)]
            print(readout)
            if readout != expected:
                raise ValueError("Pattern monitor error, iface {}, edge {}, expected: {:x} got: {:x}".format(
                    iface, "rising" if rising_edge else "falling", expected, readout))
            else:
                i += 1
        

WE = 1 << 16

@cocotb.test()
def first_test(dut):
    tb = TbPhaser(dut)

    test_pattern_a = [0x7A7A, 0x1A1A]
    test_pattern_b = [0xB6B6, 0x1616]

    yield RisingEdge(dut.phaser_pll_locked)
    yield Timer(100, 'ns')

    monitor_a = cocotb.fork(tb.test_pattern_monitor("ab", True, test_pattern_a))
    monitor_b = cocotb.fork(tb.test_pattern_monitor("ab", False, test_pattern_b))

    yield tb.spi.transfer(0x2 << 17 | WE | (1 << 5), 24)
    yield tb.spi.transfer(0x2 << 17 | WE | (1 << 6) | (1 << 5), 24)
    yield tb.spi.transfer(0x2 << 17 | WE | (1 << 6) | (1 << 5) | (1 << 4), 24)
    yield Timer(1.2, 'us')

    yield tb.spi.transfer(0x2 << 17 | WE | (1 << 6) | (1 << 5), 24)
    yield tb.spi.transfer(0x2 << 17 | WE | (1 << 5), 24)
    yield Timer(500, 'ns')

    monitor_a.kill()
    monitor_b.kill()

    # yield tb.spi.transfer(0x2 << 17 | WE | (7 << 4), 24)
    # yield Timer(500, 'ns')

    # yield tb.spi.transfer(0x2 << 17 | WE | (0), 24)
    # yield Timer(500, 'ns')

