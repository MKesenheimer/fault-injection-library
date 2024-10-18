#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# This file is based on TAoFI-FaultLib which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-FaultLib/LICENSE for full license details.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

"""
findus - Python library to perform fault-injection attacks on embedded devices.

.. code-block:: python

    # import the PicoGlitcher from findus
    from findus import Database, PicoGlitcher

    # setup PicoGlitcher
"""

import os

class Database():
    """
    Database class.
    """
    def __init__(self, argv, dbname=None, resume=False, nostore=False):
        self.nostore = nostore
        if not os.path.isdir('databases'):
            os.mkdir("databases")