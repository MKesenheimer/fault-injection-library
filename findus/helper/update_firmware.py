#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: info@faultyhardware.de.

import argparse
import os
import sys
import findus
from findus.helper import upload

def files_for_version(version: str) -> list[str]:
    """
    """
    files = ["AD910X.py", "FastADC.py", "Globals.py", "PicoGlitcher.py", "PulseGenerator.py", "Spline.py", "Statemachines.py"]
    if version == 'v1':
        files.append("config_v1/config.json")
    elif version == 'v2.1' or version == 'v2.2':
        files.append("config_v2.1-2/config.json")
    elif version == 'v2.3' or version == 'v2.4':
        files.append("config_v2.3-4/config.json")
    elif version == 'v2.5' or version == 'v3.0':
        files.append("config_v3.0/config.json")
    else:
        print(f"[-] Version string {version} not allowed. Choose either v1, v2.1, v2.2, v2.3, v2.4, v2.5 or v3.0.")
        sys.exit(-1)
    module_path = os.path.dirname(os.path.abspath(findus.__file__))
    firmware_path = os.path.join(module_path, "firmware")
    print(f"[+] Using base path {firmware_path}")
    files_with_path = [os.path.join(firmware_path, f) for f in files]
    return files_with_path

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description="Upload a micro python script to the Raspberry Pi Pico."
    )
    parser.add_argument("--port", help="/dev/tty* of the Raspberry Pi Pico", required=True, default='/dev/ttyACM1')
    parser.add_argument("--version", help="Pico Glitcher (one of v1, v2.1, v2.2, v2.3, v2.4, v2.5, v3.0)", required=False, default='v3.0')
    args = parser.parse_args()

    # get the file list
    files = files_for_version(args.version)

    # reset before tasks to have a well defined state
    upload.reset(args.port)

    pyb = upload.connect(args.port)
    remote_files = upload.list_remote_files(pyb)

    print("[+] Deleting all files...")
    upload.delete_files(pyb, remote_files)

    pyb.exit_raw_repl()
    pyb.close()

    upload.upload_files_batch(files, args.port)
    upload.reset(args.port)

    # what is on the Raspberry Pi Pico?
    upload.print_remote_content(args.port)

if __name__ == "__main__":
    main()