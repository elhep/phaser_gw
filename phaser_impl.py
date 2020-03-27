from migen.build.generic_platform import *
from migen.build.xilinx import XilinxPlatform


_io = [

    # LVDS Control Lines

    ("lvds", 0,
         Subsignal("p", Pins("W19")),
         Subsignal("n", Pins("W20")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 1,
         Subsignal("p", Pins("T21")),
         Subsignal("n", Pins("U21")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 2,
         Subsignal("p", Pins("W21")),
         Subsignal("n", Pins("W22")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 3,
         Subsignal("p", Pins("R18")),
         Subsignal("n", Pins("T18")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 4,
         Subsignal("p", Pins("U20")),
         Subsignal("n", Pins("V20")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 5,
         Subsignal("p", Pins("P19")),
         Subsignal("n", Pins("R19")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 6,
         Subsignal("p", Pins("V18")),
         Subsignal("n", Pins("V19")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 7,
         Subsignal("p", Pins("V17")),
         Subsignal("n", Pins("W17")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 8,
         Subsignal("p", Pins("Y18")),
         Subsignal("n", Pins("Y19")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 9,
         Subsignal("p", Pins("AA19")),
         Subsignal("n", Pins("AB20")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 10,
         Subsignal("p", Pins("AA20")),
         Subsignal("n", Pins("AA21")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 11,
         Subsignal("p", Pins("AA18")),
         Subsignal("n", Pins("AB18")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 12,
         Subsignal("p", Pins("AB21")),
         Subsignal("n", Pins("AB22")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 13,
         Subsignal("p", Pins("Y21")),
         Subsignal("n", Pins("Y22")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 14,
         Subsignal("p", Pins("U17")),
         Subsignal("n", Pins("U18")),
         IOStandard("LVDS_25")
     ),

    ("lvds", 15,
         Subsignal("p", Pins("P14")),
         Subsignal("n", Pins("R14")),
         IOStandard("LVDS_25")
     ),

    # ADC Interface

    ("adc_clkout", 0,
     Subsignal("p", Pins("K18")),
     Subsignal("n", Pins("K19")),
     IOStandard("LVDS_25")
     ),

    ("adc_cnvn", 0,
     Subsignal("p", Pins("H22")),
     Subsignal("n", Pins("J22")),
     IOStandard("LVDS_25")
     ),

    ("adc_sck", 0,
     Subsignal("p", Pins("M22")),
     Subsignal("n", Pins("N22")),
     IOStandard("LVDS_25")
     ),

    ("adc_sdoa", 0,
     Subsignal("p", Pins("K21")),
     Subsignal("n", Pins("K22")),
     IOStandard("LVDS_25")
     ),

    ("adc_sdob", 0,
     Subsignal("p", Pins("L21")),
     Subsignal("n", Pins("M21")),
     IOStandard("LVDS_25")
     ),

    # DAC Interface

    ("dac_alarm", 0, Pins("AB8"), IOStandard("LVCMOS33")),
    ("dac_resetb", 0, Pins("Y7"), IOStandard("LVCMOS33")),
    ("dac_sclk", 0, Pins("U7"), IOStandard("LVCMOS33")),
    ("dac_sdenb", 0, Pins("Y9"), IOStandard("LVCMOS33")),
    ("dac_sdio", 0, Pins("W9"), IOStandard("LVCMOS33")),
    ("dac_sdo", 0, Pins("AA8"), IOStandard("LVCMOS33")),
    ("dac_sleep", 0, Pins("Y8"), IOStandard("LVCMOS33")),
    ("dac_txena", 0, Pins("V8"), IOStandard("LVCMOS33")),

    # Mixer Interface

    ("trf_le", 0, Pins("T1"), IOStandard("LVCMOS33")),
    ("trf_data", 0, Pins("T3"), IOStandard("LVCMOS33")),
    ("trf_clk", 0, Pins("U3"), IOStandard("LVCMOS33")),
    ("trf_ps", 0, Pins("U1"), IOStandard("LVCMOS33")),
    ("trf_rdbk", 0, Pins("V9"), IOStandard("LVCMOS33")),
    ("trf_ld", 0, Pins("U2"), IOStandard("LVCMOS33")),

    ("trf_le", 1, Pins("W2"), IOStandard("LVCMOS33")),
    ("trf_data", 1, Pins("W1"), IOStandard("LVCMOS33")),
    ("trf_clk", 1, Pins("Y1"), IOStandard("LVCMOS33")),
    ("trf_ps", 1, Pins("W7"), IOStandard("LVCMOS33")),
    ("trf_rdbk", 1, Pins("V7"), IOStandard("LVCMOS33")),
    ("trf_ld", 1, Pins("V2"), IOStandard("LVCMOS33")),

    # Misc signals

    ("led", 0, Pins("V5"), IOStandard("LVCMOS33")),
    ("led", 1, Pins("U6"), IOStandard("LVCMOS33")),
    ("led", 2, Pins("AA3"), IOStandard("LVCMOS33")),
    ("led", 3, Pins("W4"), IOStandard("LVCMOS33")),
    ("led", 4, Pins("AA4"), IOStandard("LVCMOS33")),
    ("led", 5, Pins("W5"), IOStandard("LVCMOS33")),

    ("term_stat", 0, Pins("Y6 W6"), IOStandard("LVCMOS33")),

    ("gain", 0, Pins("AA5 AB5"), IOStandard("LVCMOS33")),
    ("gain", 1, Pins("AB6 AA6"), IOStandard("LVCMOS33")),

    ("att_rstn", 0, Pins("V3 T4"), IOStandard("LVCMOS33")),
    ("fan_pwm", 0, Pins("AB7"), IOStandard("LVCMOS33")),
    ("clk_sel", 0, Pins("T20"), IOStandard("LVCMOS25")),

    ("hw_rev", 0, Pins("N18 M17 M15 M16"), IOStandard("LVCMOS25")),
    ("assy_variant", 0, Pins("N19"), IOStandard("LVCMOS25")),

    ("clk125", 0,
        Subsignal("p", Pins("F10")),
        Subsignal("n", Pins("E10")),
    ),

]


class Platform(XilinxPlatform):

    def __init__(self):

        XilinxPlatform.__init__(
                self, "xc7a100t-fgg484-3", _io,
                toolchain="vivado")
        # self.add_platform_command(
        #         "set_property INTERNAL_VREF 0.750 [get_iobanks 35]")
        self.toolchain.bitstream_commands.extend([
            "set_property BITSTREAM.CONFIG.OVERTEMPPOWERDOWN Enable [current_design]",
            "set_property BITSTREAM.GENERAL.COMPRESS True [current_design]",
            "set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]",
            "set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 2 [current_design]",
            # "set_property BITSTREAM.CONFIG.USR_ACCESS TIMESTAMP [current_design]",
            # "set_property BITSTREAM.CONFIG.USERID \"{:#010x}\" [current_design]".format(self.userid),
            "set_property CFGBVS VCCO [current_design]",
            "set_property CONFIG_VOLTAGE 2.5 [current_design]",
            ])
