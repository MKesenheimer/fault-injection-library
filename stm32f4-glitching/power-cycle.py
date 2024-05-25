#!/usr/bin/env python3
import argparse
import logging
import random
import sys
import time

# import custom libraries
sys.path.insert(0, "../lib/")
from FaultInjectionLib import ProGlitcher

glitcher = ProGlitcher()
glitcher.init()
glitcher.power_cycle_target()
