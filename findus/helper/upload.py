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

def upload(file:str, port:str):
    try:
        ret = subprocess.check_output(["ampy", "-p", port, "ls"])
    except Exception as e:
        print("[-] Pico Glitcher could not be found. Aborting.")
        sys.exit(-1)
    filename = os.path.basename(file)
    if filename.encode() in ret:
        print(f"[+] Deleting {filename}...")
        subprocess.call(["ampy", "-p", port, "rm", filename])

    # upload the new script
    print(f"[+] Uploading {file}...")
    subprocess.call(["ampy", "-p", port, "put", file])

def reset(port:str):
    # resetting
    print("[+] Resetting Raspberry Pi Pico...")
    subprocess.call(["ampy", "-p", port, "reset"])

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description="Upload a micro python script to the Raspberry Pi Pico."
    )
    parser.add_argument("--port", help="/dev/tty* of the Raspberry Pi Pico", required=True, default='/dev/ttyACM1')
    parser.add_argument("--delete-all", help="Delete all files from the Raspberry Pi Pico", required=False, action='store_true')
    parser.add_argument("--delete", help="Delete the file from the Raspberry Pi Pico", required=False, default=None)
    parser.add_argument("--file", help="File to upload to the Raspberry Pi Pico", required=False, default=None)
    parser.add_argument("--files", nargs='+', help="Files to upload to the Raspberry Pi Pico", required=False, default=None)
    args = parser.parse_args()

    # reset before tasks to have a well defined state
    reset(args.port)

    try:
        ret = subprocess.check_output(["ampy", "-p", args.port, "ls"])
    except Exception as _:
        print("[-] Pico Glitcher could not be found. Aborting.")
        sys.exit(-1)
    if args.delete_all:
        print("[+] Deleting all files...")
        for filename in ret.decode().split():
            subprocess.call(["ampy", "-p", args.port, "rm", filename[1:]])

    if args.delete:
        filename = os.path.basename(args.delete)
        if filename.encode() in ret:
            print(f"[+] Deleting {filename}...")
            subprocess.call(["ampy", "-p", args.port, "rm", filename])

    if args.file is not None:
        upload(args.files, args.port)
        reset(args.port)

    if args.files is not None:
        for f in args.files:
            upload(f, args.port)
        reset(args.port)

    # what is on the Raspberry Pi Pico?
    print("[+] Content of the Raspberry Pi Pico:")
    subprocess.call(["ampy", "-p", args.port, "ls"])

if __name__ == "__main__":
    main()