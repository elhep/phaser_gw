# (S3[15:0]) (S2[15:0]) (S1[15:0]) (S0[15:0])

memory_contents = {
    "length": 8,
    "a": [
        0x7A7A1A1A7A7A1A1A,
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

if memory_contents['length'] % 4 != 0:
    raise ValueError("Invalid memory length! ({}%4!=0)".format(memory_contents['length']))