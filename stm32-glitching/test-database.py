# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import sys

# import custom libraries
sys.path.insert(0, "../lib/")
from FaultInjectionLib import Database

database = Database(sys.argv)
database.insert(0, 1000, 10, 'R', b'Test')
database.insert(1, 1000, 10, 'R', b'Test')

database.remove(0)