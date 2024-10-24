#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# This file is based on TAoFI-FaultLib which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-FaultLib/LICENSE for full license details.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import argparse
import subprocess
import os
import sys

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description="Upload a micro python script to the Raspberry Pi Pico."
    )
    parser.add_argument("--port", help="/dev/tty* of the Raspberry Pi Pico", required=False, default='/dev/ttyACM1')
    parser.add_argument("--delete-all", help="delete all micro python scripts from the Raspberry Pi Pico", required=False, action='store_true')
    parser.add_argument("--script", help="micro python script to upload to the Raspberry Pi Pico", required=False, default=None)
    args = parser.parse_args()

    ret = subprocess.check_output(["ampy", "-p", args.port, "ls"])
    if args.delete_all:
        print("[+] Deleting all micro python scripts on the Raspberry Pi Pico...")
        for filename in ret.decode().split():
            subprocess.call(["ampy", "-p", args.port, "rm", filename[1:]])
        print("[+] Done.")
    
    if args.script is not None:
        filename = os.path.basename(args.script)
        if filename.encode() in ret:
            print("[+] Deleting old micro python script...")
            subprocess.call(["ampy", "-p", args.port, "rm", filename])
            print("[+] Done.")

        # put the new state machine
        print("[+] Uploading new micro python script...")
        subprocess.call(["ampy", "-p", args.port, "put", args.script])
        print("[+] Done.")

        # resetting
        print("[+] Resetting Raspberry Pi Pico...")
        subprocess.call(["ampy", "-p", args.port, "reset"])
        print("[+] Done.")

    # what is on the Raspberry Pi Pico?
    print("[+] Content of the Raspberry Pi Pico:")
    subprocess.call(["ampy", "-p", args.port, "ls"])

if __name__ == "__main__":
    main()