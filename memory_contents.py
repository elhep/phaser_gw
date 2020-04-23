# (S3[15:0]) (S2[15:0]) (S1[15:0]) (S0[15:0])

memory_contents = {
    "test_pattern": {
        "length": 8,
        "a": [
            0x7A7A1A1A7A7A1B1A,
            0x7A7A1A1A7A7A1A1A
        ],
        "b": [
            0xB6B61616B6B61616,
            0xB6B61616B6B61616
        ],
        "c": [
            0xEAEAAAAAEAEAAAAA,
            0xEAEAAAAAEAEAAAAA
        ],
        "d": [
            0x4545C6C64545C6C6,
            0x4545C6C64545C6C6
        ],
    }
}

from math import sin, pi

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def to_mem_row(vals):
    out = 0
    for i,v in enumerate(vals):
        out |= v << (i*16)
    return out

def sine_wave(init_phase=0, samples_n=128):
    vmax = 2**16-1
    samples = [int(vmax/2*(1+sin(i/samples_n*2*pi+init_phase)) ) for i in range(samples_n)]
    samples = list(chunks(samples, 4))
    samples = [to_mem_row(x) for x in samples]
    return samples
    
memory_contents["sin"] = {
    "length": 128,
    "a": sine_wave(),
    "b": sine_wave(init_phase=pi/2),
    "c": sine_wave(),
    "d": sine_wave(init_phase=pi/2),
}


# memory_contents = {
#     "length": 8,
#     "a": [
#         0x1A1A7A7A1A1A7A7A,
#         0x1A1A7A7A1A1A7A7A
#     ],
#     "b": [
#         0x1616B6B61616B6B6,
#         0x1616B6B61616B6B6
#     ],
#     "c": [
#         0xAAAAEAEAAAAAEAEA,
#         0xAAAAEAEAAAAAEAEA
#     ],
#     "d": [
#         0xC6C64545C6C64545,
#         0xC6C64545C6C64545
#     ],
# }

for k, v in memory_contents.items():
    if v['length'] % 4 != 0:
        raise ValueError("Invalid memory length for {}! ({}%4!=0)".format(k, v['length']))