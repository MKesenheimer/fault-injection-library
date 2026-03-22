#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# This file is based on TAoFI-FaultLib which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-FaultLib/LICENSE for full license details.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: info@faultyhardware.de.

import argparse
import os
import sys
import stat

from findus.pyboard import Pyboard

def connect(port: str, soft_reset: bool = False) -> Pyboard:
    try:
        pyb = Pyboard(port, wait=2)
        pyb.enter_raw_repl(soft_reset=soft_reset)
        return pyb
    except Exception:
        print("[-] Pico Glitcher could not be found. Aborting.")
        sys.exit(-1)

def list_remote_files(pyb: Pyboard) -> list[str]:
    return [
        entry.name
        for entry in pyb.fs_listdir("")
        if not stat.S_ISDIR(entry.st_mode)
    ]

def delete_files(pyb: Pyboard, filenames: list[str]):
    if not filenames:
        return
    print(f"[+] Deleting files: {', '.join(filenames)}...")
    for filename in filenames:
        pyb.fs_rm(filename)

def upload_files(pyb: Pyboard, files: list[str]):
    if not files:
        return
    print(f"[+] Uploading files: {', '.join(files)}...")
    for file in files:
        pyb.fs_put(file, os.path.basename(file))

def upload(file: str, port: str):
    pyb = connect(port)
    remote_files = list_remote_files(pyb)
    filename = os.path.basename(file)
    if filename in remote_files:
        print(f"[+] Deleting {filename}...")
        pyb.fs_rm(filename)

    print(f"[+] Uploading {file}...")
    pyb.fs_put(file, filename)
    pyb.exit_raw_repl()
    pyb.close()

def upload_files_batch(files: list[str], port: str):
    pyb = connect(port)
    remote_files = set(list_remote_files(pyb))

    # delete all existing target files first (single connected session)
    target_filenames = [os.path.basename(f) for f in files]
    to_delete = [name for name in target_filenames if name in remote_files]
    if to_delete:
        delete_files(pyb, to_delete)

    # then upload everything (single connected session)
    upload_files(pyb, files)
    pyb.exit_raw_repl()
    pyb.close()

def reset(port: str):
    print("[+] Resetting Raspberry Pi Pico...")
    pyb = connect(port)
    # Use no-follow execution because the board resets immediately.
    pyb.exec_raw_no_follow("import machine\nmachine.reset()")
    pyb.close()

def print_remote_content(port: str):
    pyb = connect(port)
    print("[+] Content of the Raspberry Pi Pico:")
    for filename in list_remote_files(pyb):
        print(filename)
    pyb.exit_raw_repl()
    pyb.close()

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

    pyb = connect(args.port)
    remote_files = list_remote_files(pyb)
    remote_file_set = set(remote_files)

    if args.delete_all:
        print("[+] Deleting all files...")
        delete_files(pyb, remote_files)

    if args.delete:
        filename = os.path.basename(args.delete)
        if filename in remote_file_set:
            print(f"[+] Deleting {filename}...")
            pyb.fs_rm(filename)

    pyb.exit_raw_repl()
    pyb.close()

    if args.file is not None:
        upload(args.file, args.port)
        reset(args.port)

    if args.files is not None:
        upload_files_batch(args.files, args.port)
        reset(args.port)

    # what is on the Raspberry Pi Pico?
    print_remote_content(args.port)

if __name__ == "__main__":
    main()
