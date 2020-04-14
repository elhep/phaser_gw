import argparse

from migen import *
from phaser_impl import Platform
from migen.genlib.io import DifferentialInput, DifferentialOutput
from migen.genlib.cdc import MultiReg, AsyncResetSynchronizer
from migen.genlib.fsm import *
from memory_contents import memory_contents


# increment this if the behavior (LEDs, registers, EEM pins) changes
__proto_rev__ = 0


class AsyncRst(Module):
    def __init__(self, width=None, cd="sys", reset=0, **kwargs):
        self.i = Signal(width, reset=reset, **kwargs)
        self.o = Signal(width, **kwargs)
        self.ce = Signal(reset=1)
        for i in range(len(self.i)):
            ini = (reset >> i) & 1
            self.specials += Instance("FDCPE",
                                      p_INIT=ini,
                                      i_D=self.i[i],
                                      i_C=ClockSignal(cd),
                                      i_CE=self.ce,
                                      i_PRE=ResetSignal(cd) if ini else 0,
                                      i_CLR=ResetSignal(cd) if not ini else 0,
                                      o_Q=self.o[i])


bus_layout = [
    ("adr", 7),
    ("re", 1),
    ("dat_r", 16),
    ("we", 1),
    ("dat_w", 16),
]

ext_layout = [
    ("cs", 1),
    ("sck", 1),
    ("sdo", 1),
    ("sdi", 1),
]


class REG(Module):
    def __init__(self, width=None, read=True, write=True):
        self.bus = Record(bus_layout)
        if width is None:
            width = len(self.bus.dat_w)
        assert width <= len(self.bus.dat_w)
        if write:
            self.write = Signal(width)
            self.sync.reg += If(self.bus.we, self.write.eq(self.bus.dat_w))
        if read:
            self.read = Signal(width)
            self.comb += self.bus.dat_r.eq(self.read)


# R,F edges happen left in each column

# CSN  -F__________R
# LI    L
# LO               L
# CLK   _RFRFRFRFRF_
#fMOSI  AABBWW0011
#rSDI    AABBWW0011
#fWE            WW
#fRE        11
#fSDO         0011
#fMISO        0011
#fN     443162110004
#fN A   332211000003
#fN D   222222221102
#
# default: falling
# MOSI->SDI: rising

class SR(Module):
    def __init__(self):
        self.bus = Record(bus_layout)
        self.ext = Record(ext_layout)

        self._slaves = []

        sdi = Signal(reset_less=True)
        sr_adr = Signal(len(self.bus.adr), reset_less=True)
        sr_dat = Signal(len(self.bus.dat_w), reset_less=True)
        we = Signal(reset_less=True)

        width = len(sr_adr) + 1 + len(sr_dat)
        # bits to be transferred - 1
        n = AsyncRst(max=width, reset=width - 1)
        p = AsyncRst()
        self.submodules += n, p

        self.comb += [
            n.i.eq(n.o - 1),
            n.ce.eq(n.o != 0),
            p.i.eq(1),
            p.ce.eq(n.o == len(sr_dat)),

            self.ext.sdo.eq(sr_dat[-1]),

            self.bus.adr.eq(sr_adr),
            self.bus.dat_w.eq(Cat(sdi, sr_dat)),
            self.bus.re.eq(p.ce),
            self.bus.we.eq(~n.ce & we),
        ]
        self.sync.sck += sdi.eq(self.ext.sdi)
        self.sync += [
            sr_dat.eq(self.bus.dat_w),
            If(p.ce,
                we.eq(sdi),
                sr_dat.eq(self.bus.dat_r),
            ).Elif(~p.o,
                sr_adr.eq(Cat(sdi, sr_adr)),
            )
        ]

    def _check_intersection(self, adr, mask):
        for _, b_adr, b_mask in self._slaves:
            if intersection((b_adr, b_mask), (adr, mask)):
                raise ValueError("{} intersects {}".format(
                    (adr, mask), (b_adr, b_mask)))

    def connect(self, bus, adr, mask):
        adr &= mask
        self._check_intersection(adr, mask)
        self._slaves.append((bus, adr, mask))
        stb = Signal()
        self.comb += [
            stb.eq(self.bus.adr & mask == adr),
            bus.adr.eq(self.bus.adr),
            bus.dat_w.eq(self.bus.dat_w),
            bus.we.eq(self.bus.we & stb),
            bus.re.eq(self.bus.re & stb),
            If(stb,
                self.bus.dat_r.eq(bus.dat_r)
            )
        ]

    def connect_ext(self, ext, adr, mask):
        adr &= mask
        self._check_intersection(adr, mask)
        self._slaves.append((ext, adr, mask))
        stb = AsyncRst()
        self.submodules += stb
        self.comb += [
            stb.i.eq(self.bus.adr & mask == adr),
            stb.ce.eq(self.bus.re),
            # don't glitch with &stb.o
            ext.sck.eq(self.ext.sck),
            ext.sdi.eq(self.ext.sdi & stb.o),
            ext.cs.eq(stb.o),
            If(stb.o,
                self.ext.sdo.eq(ext.sdo),
            ),
        ]


def intersection(a, b):
    (aa, am), (ba, bm) = a, b
    # TODO
    return False


class Phaser(Module):
    """
    Phaser IO router and configuration/status
    ========================================

    Pin Out
    -------

    | EEM LVDS pair | Function               |
    |---------------+------------------------|
    | EEM 0         | SCLK                   |
    | EEM 1         | MOSI                   |
    | EEM 2         | MISO                   |
    | EEM 3         | CS                     |

    SPI
    ---

    SPI xfer is ADR(7), WE(1), DAT(REG: 16, ATT: 8, DAC: 16, MOD: 32)

    | ADR | TARGET |
    |-----+--------|
    | 0   | REG0   |
    | 1   | REG1   |
    | 2   | REG2   |
    | 3   | REG3   |
    | 4   | REG4   |
    | 5   | DAC    |
    | 6   | MOD0   |
    | 7   | MOD1   |
    | 8   | ATT0   |
    | 9   | ATT1   |

    The SPI interface is CPOL=0, CPHA=0, SPI mode 0, 4-wire, full fuplex.

    Configuration register

    The status bits are read on the falling edge of after the WE bit (8th
    falling edge).
    The configuration bits are updated at the last falling SCK edge of the SPI
    transaction (24th falling edge). The initial state is 0 (all bits cleared).
    The bits in the registers (from LSB to MSB) are:

    REG0 - Miscellaneous status

    | Name      | Width | Function                           | Python
    |-----------+-------+------------------------------------|
    | CLK_TEST  | 1     | GTP clock test                     |   9
    | ASSY_VAR  | 1     | Assembly variant:                  |  8:9
    |           |       | 0: upconverter                     |
    |           |       | 1: baseband                        |  
    | PROTO_REV | 2     | Protocol revision                  |  6:8
    | HW_REV    | 4     | Hardware revision                  |  2:6
    | TERM      | 2     | Termination, active high (readout) |  0:2
    
    REG1 - Miscellaneous control
    
    | ATT_RSTn  | 2     | Attenuator reset, active low       |  7:9
    | CLK_SEL   | 1     | Clock source select:               |  6:7
    |           |       | 0: MMCX                            |
    |           |       | 1: SMA                             |
    | LED       | 6     | LED state                          |  0:6

    REG2 - DAC control / status

    | Name      | Width | Function                           |
    |-----------+-------+------------------------------------|
    | DAC_TESTen| 1     | DAC test pattern enabled           |  6
    | DAC_IFRSTn| 1     | DAC interface reset, active low    |  5
    | DAC_PLAY  | 1     | Play samples embedded in BRAM      |  4
    | DAC_ALARM | 1     | State of DAC alarm pin             |  3
    | DAC_RESETn| 1     | DAC reset, active low              |  2
    | DAC_SLEEP | 1     | DAC sleep, active high             |  1
    | DAC_TXENA | 1     | DAC TX Enabled, active high        |  0

    REG3 - Attenuators control

    | Name      | Width | Function                           |
    |-----------+-------+------------------------------------|
    | CH0_GAIN  | 2     | Channel 0 gain                     |  2:4
    |           |       | 00: 1                              |
    |           |       | 01: 10                             |
    |           |       | 10: 100                            |
    |           |       | 11: 1000                           |
    | CH1_GAIN  | 2     | Channel 1 gain                     |  0:2
    |           |       | 00: 1                              |
    |           |       | 01: 10                             |
    |           |       | 10: 100                            |
    |           |       | 11: 1000                           |

    REG4 - Upconverter control / status

    | Name      | Width | Function                           |
    |-----------+-------+------------------------------------|
    | LOCK DET  | 2     | Lock detect (redout)               |  2:4
    | PWR SAVE  | 2     | Power saving enabled, active high  |  0:2

    """
    def __init__(self, platform, memory_contents):
        self.eem = eem = [Signal() for _ in range(4)]
        eemi = [platform.request("lvds", i) for i in range(4)]
        for i, (sig, pad) in enumerate(zip(eem, eemi)):
            if i in (2,):  # Output
                self.specials += DifferentialOutput(sig, pad.p, pad.n)
            else:  # Input
                self.specials += DifferentialInput(pad.p, pad.n, sig)

        platform.add_period_constraint(eemi[0].p, 8.)
        platform.add_period_constraint(eemi[3].p, 8.)
    
        self.clock_domains.cd_sys = ClockDomain("sys")
        self.clock_domains.cd_sck = ClockDomain("sck")
        self.clock_domains.cd_reg = ClockDomain("reg", reset_less=True)

        self.specials += [
            Instance("BUFG",
                     i_I=eem[0],
                     o_O=self.cd_sck.clk),
        ]
        self.comb += [
            self.cd_sck.rst.eq(~eem[3]),
            self.cd_sys.clk.eq(~self.cd_sck.clk),
            self.cd_sys.rst.eq(self.cd_sck.rst),
            self.cd_reg.clk.eq(self.cd_sys.clk),
        ]

        self.submodules.sr = SR()
        mask = 0b0001111

        self.comb += [
            self.sr.ext.sck.eq(self.cd_sck.clk),
            self.sr.ext.sdi.eq(eem[1]),
            eem[2].eq(self.sr.ext.sdo),
            self.sr.ext.cs.eq(eem[3]),
        ]

        # Registers

        regs = [
            REG(width=10),
            REG(width=9),
            REG(width=7),
            REG(width=4),
            REG(width=4)
        ]
        self.submodules += regs
        for i, reg in enumerate(regs):
            self.sr.connect(reg.bus, adr=i, mask=mask)

        clk_gtp_test = Signal()
        assy_variant = platform.request("assy_variant")
        hw_rev = platform.request("hw_rev")
        term_stat = platform.request("term_stat")

        led_pads = [platform.request("led", i) for i in range(6)]
        att_rstn = platform.request("att_rstn")
        clk_sel = platform.request("clk_sel")
        
        dac_ifreset = Signal()
        dac_test_pattern_en = Signal()
        dac_play = Signal()
        dac_alarm = platform.request("dac_alarm")
        dac_resetb = platform.request("dac_resetb")
        dac_sleep = platform.request("dac_sleep")
        dac_txena = platform.request("dac_txena")

        gain_ch0 = platform.request("gain", 0)
        gain_ch1 = platform.request("gain", 1)

        trf_ld = Cat(*[platform.request("trf_ld", i) for i in [1,0]])
        trf_ps = Cat(*[platform.request("trf_ps", i) for i in [1,0]])

        self.comb += [
            # Readout
            regs[0].read.eq(Cat(term_stat, hw_rev, Constant(__proto_rev__, 2), assy_variant, clk_gtp_test)),
            regs[1].read.eq(regs[1].write),
            regs[2].read.eq(Cat(regs[2].write[0:3], dac_alarm, dac_play, dac_ifreset, dac_test_pattern_en)),
            regs[3].read.eq(regs[3].write),
            regs[4].read.eq(Cat(regs[0].write[0:2], trf_ld)),

            *[led_pads[i].eq(regs[1].write[i]) for i in range(6)],
            clk_sel.eq(regs[1].write[6]),
            att_rstn.eq(regs[1].write[7:9]),

            dac_test_pattern_en.eq(regs[2].write[6]),
            dac_ifreset.eq(~regs[2].write[5]),
            dac_play.eq(regs[2].write[4]),
            dac_resetb.eq(regs[2].write[2]),
            dac_sleep.eq(regs[2].write[1]),
            dac_txena.eq(regs[2].write[0]),

            gain_ch0.eq(regs[3].write[0:2]),
            gain_ch1.eq(regs[3].write[2:4]),

            trf_ps.eq(regs[4].write[0:2])
        ]

        self.clock_domains.cd_dac_clk = ClockDomain()
        self.clock_domains.cd_dac_clk4x = ClockDomain(reset_less=True)
        self.clock_domains.cd_clk125_div2 = ClockDomain(reset_less=True)
        self.clock_domains.cd_clk_gtp_div2 = ClockDomain(reset_less=True)

        clk125_div2 = Signal()
        clk125m_pads = platform.request("clk125")
        self.specials += Instance("IBUFDS_GTE2", o_ODIV2=clk125_div2, i_I=clk125m_pads.p, i_IB=clk125m_pads.n, i_CEB=False)
        self.cd_clk125_div2.clk.attr.add(("keep", "true"))
        self.cd_clk125_div2.clk.attr.add(("mark_dbg_hub_clk", "true"))
        self.specials += Instance("BUFG", i_I=clk125_div2, o_O=self.cd_clk125_div2.clk)
        platform.add_period_constraint(self.cd_clk125_div2.clk, 16.)

        clk_gtp_div2 = Signal()
        clk_gtp_pads = platform.request("clk_gtp")
        self.specials += Instance("IBUFDS_GTE2", o_ODIV2=clk_gtp_div2, i_I=clk_gtp_pads.p, i_IB=clk_gtp_pads.n, i_CEB=False)
        self.specials += Instance("BUFG", i_I=clk_gtp_div2, o_O=self.cd_clk_gtp_div2.clk)
        platform.add_period_constraint(self.cd_clk_gtp_div2.clk, 16.)

        clock_tester_gtp = Signal(reset=0)
        cnt_gtp = Signal(max=1023, reset=1023)
        self.comb += clock_tester_gtp.eq(cnt_gtp == 0)
        self.sync.clk_gtp_div2 += If(cnt_gtp != 0, cnt_gtp.eq(cnt_gtp-1))
        self.specials += MultiReg(clock_tester_gtp, clk_gtp_test, "sys")

        pll_locked = Signal()
        dac_clk = Signal()
        dac_clk4x = Signal()
        dac_clk_shift = Signal()
        dac_clk4x_shift = Signal()
        fb_clk = Signal()
        # pll_clk200 = Signal()
        
        self.specials += [
            Instance("PLLE2_BASE",
                     p_STARTUP_WAIT="FALSE", 
                     p_BANDWIDTH="HIGH",
                     p_CLKIN1_PERIOD=16.0, 
                     p_CLKFBOUT_MULT=16, # VCO 1000 MHz
                     p_DIVCLK_DIVIDE=1,
                     
                     i_CLKIN1=ClockSignal("clk125_div2"),
                     i_CLKFBIN=fb_clk,
                     o_CLKFBOUT=fb_clk,

                    #  i_RST=self.cd_sys.rst,
                     o_LOCKED=pll_locked,

                     p_CLKOUT0_DIVIDE=8, p_CLKOUT0_PHASE=0.0,
                     o_CLKOUT0=dac_clk4x,  # 125 MHz

                     p_CLKOUT1_DIVIDE=32, p_CLKOUT1_PHASE=0.0,
                     o_CLKOUT1=dac_clk,   # 32.5 MHz

                     p_CLKOUT2_DIVIDE=8, p_CLKOUT2_PHASE=90,
                     o_CLKOUT2=dac_clk4x_shift,

                     p_CLKOUT3_DIVIDE=32, p_CLKOUT3_PHASE=90,
                     o_CLKOUT3=dac_clk_shift
                     
                 
                     ),
            Instance("BUFG", i_I=dac_clk, o_O=self.cd_dac_clk.clk),
            Instance("BUFG", i_I=dac_clk4x, o_O=self.cd_dac_clk4x.clk),
            AsyncResetSynchronizer(self.cd_dac_clk, ~pll_locked),
        ]
        platform.add_period_constraint(self.cd_dac_clk.clk, 8.)
        platform.add_period_constraint(self.cd_dac_clk4x.clk, 2.)

        dac_play_dac_clk = Signal()
        dac_oe = Signal()
        dac_sample_address = Signal()
        self.specials += MultiReg(dac_play, dac_play_dac_clk, "dac_clk")

        pattern_length = memory_contents['length']
        memory_depth = pattern_length // 4
        memory_address = Signal(max=memory_depth)

        dac_istr = Signal()
        self.specials += DifferentialOutput(dac_istr, platform.request("dac_istr_p"), platform.request("dac_istr_n"))

        fsm = ClockDomainsRenamer("dac_clk")(FSM(reset_state="IDLE"))
        self.submodules += fsm
        
        fsm.act("IDLE", 
                NextValue(dac_oe, 0),
                NextValue(dac_istr, 0),
                NextValue(memory_address, 0),
                If(dac_play_dac_clk,
                   NextValue(dac_istr, 1),
                   NextState("PLAY"),
                   NextValue(memory_address, memory_address+1),
                   NextValue(dac_oe, 1),
                )
        )

        fsm.act("PLAY",
                NextValue(dac_oe, 1),
                NextValue(dac_istr, 0),
                If(~dac_play_dac_clk,
                    NextState("IDLE"),
                    NextValue(dac_oe, 0),
                ),
                If(memory_address >= memory_depth-1,
                    NextValue(memory_address, 0), 
                ).Else(
                   NextValue(memory_address, memory_address+1)
                )
        )

        dac_channel_data = {
            "a": Signal(64),
            "b": Signal(64),
            "c": Signal(64),
            "d": Signal(64)
        }

        dac_test_patterns = {
            "a": Signal(64, reset=0x1A1A7A7A1A1A7A7A),
            "b": Signal(64, reset=0x1616B6B61616B6B6),
            "c": Signal(64, reset=0xAAAAEAEAAAAAEAEA),
            "d": Signal(64, reset=0xC6C64545C6C64545)
        }
        dac_test_pattern_mask = Signal(64)

        for ch in "abcd":
            mem = Memory(depth=memory_depth, width=64, init=memory_contents[ch])
            read_port = mem.get_port(clock_domain="dac_clk")
            self.specials += mem, read_port
            
            self.comb += [
                read_port.adr.eq(memory_address),
                If(dac_test_pattern_en, dac_test_pattern_mask.eq(0xFFFFFFFFFFFFFFFF)).Else(dac_test_pattern_mask.eq(0)),
                dac_channel_data[ch].eq(
                    (read_port.dat_r & ~dac_test_pattern_mask) | (dac_test_patterns[ch] & dac_test_pattern_mask))
            ]

        serdes_out = Signal()
        self.specials += Instance("OSERDESE2",
            p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="BUF",
            p_DATA_WIDTH=8, p_TRISTATE_WIDTH=1,
            p_INIT_OQ=0b00000000,
            o_OQ=serdes_out,
            i_RST=ResetSignal("dac_clk"),
            i_CLK=dac_clk4x_shift,
            i_CLKDIV=dac_clk_shift,
            i_D1=1,
            i_D2=0,
            i_D3=1,
            i_D4=0,
            i_D5=1,
            i_D6=0,
            i_D7=1,
            i_D8=0,
            i_TCE=1, i_OCE=dac_oe,
            i_T1=0)

        pad_p = platform.request("dac_dataclk_p", 0)
        pad_n = platform.request("dac_dataclk_n", 0)
        self.specials += Instance("OBUFDS", i_I=serdes_out, o_O=pad_p, o_OB=pad_n)

        for x,y in ["ab", "cd"]:
            for line_idx in range(16):
                pad_p = platform.request("dac_d{}_p".format("".join([x,y])), line_idx)
                pad_n = platform.request("dac_d{}_n".format("".join([x,y])) , line_idx)
                serdes_out = Signal()

                # Workaround for HW issue #102
                if ((x, y) == ("a", "b") and line_idx == 3) or ((x, y) == ("c", "d") and line_idx == 8):
                    self.specials += Instance("OSERDESE2",
                        p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="BUF",
                        p_DATA_WIDTH=8, p_TRISTATE_WIDTH=1,
                        p_INIT_OQ=0b00000000,
                        o_OQ=serdes_out,
                        i_RST=ResetSignal("dac_clk"),
                        i_CLK=ClockSignal("dac_clk4x"),
                        i_CLKDIV=ClockSignal("dac_clk"),
                        i_D1=~dac_channel_data[x][0*16+line_idx], 
                        i_D2=~dac_channel_data[y][0*16+line_idx], 
                        i_D3=~dac_channel_data[x][1*16+line_idx], 
                        i_D4=~dac_channel_data[y][1*16+line_idx], 
                        i_D5=~dac_channel_data[x][2*16+line_idx], 
                        i_D6=~dac_channel_data[y][2*16+line_idx], 
                        i_D7=~dac_channel_data[x][3*16+line_idx], 
                        i_D8=~dac_channel_data[y][3*16+line_idx], 
                        i_TCE=1, i_OCE=1,
                        i_T1=0)
                    self.specials += Instance("OBUFDS", i_I=serdes_out, o_O=pad_n, o_OB=pad_p)
                else:
                    self.specials += Instance("OSERDESE2",
                        p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="BUF",
                        p_DATA_WIDTH=8, p_TRISTATE_WIDTH=1,
                        p_INIT_OQ=0b00000000,
                        o_OQ=serdes_out,
                        i_RST=ResetSignal("dac_clk"),
                        i_CLK=ClockSignal("dac_clk4x"),
                        i_CLKDIV=ClockSignal("dac_clk"),
                        i_D1=dac_channel_data[x][0*16+line_idx], 
                        i_D2=dac_channel_data[y][0*16+line_idx], 
                        i_D3=dac_channel_data[x][1*16+line_idx], 
                        i_D4=dac_channel_data[y][1*16+line_idx], 
                        i_D5=dac_channel_data[x][2*16+line_idx], 
                        i_D6=dac_channel_data[y][2*16+line_idx], 
                        i_D7=dac_channel_data[x][3*16+line_idx], 
                        i_D8=dac_channel_data[y][3*16+line_idx], 
                        i_TCE=1, i_OCE=1,
                        i_T1=0)
                    self.specials += Instance("OBUFDS", i_I=serdes_out, o_O=pad_p, o_OB=pad_n)

        # SPI buses

        # DAC
        ext = Record(ext_layout)
        self.sr.connect_ext(ext, adr=0 + len(regs), mask=mask)

        self.comb += [
            platform.request("dac_sdenb").eq(~ext.cs),
            platform.request("dac_sclk").eq(ext.sck),
            platform.request("dac_sdio").eq(ext.sdi),
            ext.sdo.eq(platform.request("dac_sdo"))
        ]

        trf_ext = []

        for i in range(2):
            ext = Record(ext_layout)
            trf_ext.append(ext)
            self.sr.connect_ext(ext, adr=1 + len(regs) + i, mask=mask)
            self.comb += [
                platform.request("trf_clk", i).eq(ext.sck),
                platform.request("trf_data", i).eq(ext.sdi),
                platform.request("trf_le", i).eq(~ext.cs),
                ext.sdo.eq(platform.request("trf_rdbk", i))
            ]

        # Debug

        # platform.toolchain.post_synthesis_commands.append(
        #     "source /home/ms/data/pw/cosyquanta/projects/phaser_debug/gateware/insert_ila.tcl")
        # platform.toolchain.post_synthesis_commands.append(
        #     "batch_insert_ila {16384}")
        # platform.toolchain.post_synthesis_commands.append(
        #     "connect_debug_port dbg_hub/clk [get_nets -hierarchical -filter {mark_dbg_hub_clk == true}]")

        # # Debug nets definition

        trf_ext[0].cs.attr.add(("mark_debug", "true"))
        trf_ext[0].cs.attr.add(("mark_debug_clock", "clk125_clk"))
        trf_ext[0].sck.attr.add(("mark_debug", "true"))
        trf_ext[0].sck.attr.add(("mark_debug_clock", "clk125_clk"))
        trf_ext[0].sdi.attr.add(("mark_debug", "true"))
        trf_ext[0].sdi.attr.add(("mark_debug_clock", "clk125_clk"))
        trf_ext[0].sdo.attr.add(("mark_debug", "true"))
        trf_ext[0].sdo.attr.add(("mark_debug_clock", "clk125_clk"))

        trf_ext[1].cs.attr.add(("mark_debug", "true"))
        trf_ext[1].cs.attr.add(("mark_debug_clock", "clk125_clk"))
        trf_ext[1].sck.attr.add(("mark_debug", "true"))
        trf_ext[1].sck.attr.add(("mark_debug_clock", "clk125_clk"))
        trf_ext[1].sdi.attr.add(("mark_debug", "true"))
        trf_ext[1].sdi.attr.add(("mark_debug_clock", "clk125_clk"))
        trf_ext[1].sdo.attr.add(("mark_debug", "true"))
        trf_ext[1].sdo.attr.add(("mark_debug_clock", "clk125_clk"))

        # dac_csn.attr.add(("mark_debug", "true"))
        # dac_sclk.attr.add(("mark_debug", "true"))
        # dac_sdi.attr.add(("mark_debug", "true"))
        # dac_sdo.attr.add(("mark_debug", "true"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phaser gateware builder")
    parser.add_argument("--no-compile-gateware", action="store_false", default=True,
                        help="do not compile gateware, just emit Verilog")
    parser.add_argument("--memory-contents", default="sin", help="memory contents")
    args = parser.parse_args()
    p = Platform()
    phaser = Phaser(p, memory_contents[args.memory_contents])
    p.build(phaser, build_name="phaser", run=args.no_compile_gateware)

