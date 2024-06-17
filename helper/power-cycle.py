#!/usr/bin/env python3
import sys

# import custom libraries
sys.path.insert(0, "../lib/")
from FaultInjectionLib import ProGlitcher

print("[+] Initializing ProGlitcher")
glitcher = ProGlitcher()
glitcher.init()
print("[+] Power cycling target.")
glitcher.power_cycle_target(1)
print("[+] Done.")