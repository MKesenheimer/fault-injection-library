import sys

# import custom libraries
sys.path.insert(0, "../lib/")
from FaultInjectionLib import Database

database = Database(sys.argv)
database.insert(0, 1000, 10, 'R', b'Test')
database.insert(1, 1000, 10, 'R', b'Test')

database.remove(0)