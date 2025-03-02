#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

from enum import Enum

# types for classification
class ErrorType(Enum):
    pass

class WarningType(Enum):
    pass

class OKType(Enum):
    pass

class ExpectedType(Enum):
    pass

class SuccessType(Enum):
    pass

# templates to copy
class _Expected(ExpectedType):
    """
    Enum class for expected states.
    """
    default = 0
    rdp_active = 1

class _Error(ErrorType):
    """
    Enum class for error states.
    """
    default = 0
    nack = 1
    no_response = 2
    bootloader_not_available = 3
    bootloader_error = 4
    id_error = 5

class _Warning(WarningType):
    """
    Enum class for warning states.
    """
    default = 0
    flash_reset = 1
    timeout = 2

class _OK(OKType):
    """
    Enum class for ok states (no errors).
    """
    default = 0
    ack = 1
    bootloader_ok = 2
    dump_error = 4

class _Success(SuccessType):
    """
    Enum class for success states (glitching was successful).
    """
    default = 0
    rdp_inactive = 1
    dump_ok = 2
    dump_successful = 3
    dump_finished = 4

class GlitchState():
    """
    Class that combines subclasses for different states. Can be used to classify different responses.

    - Error: Enum class for error states.
    - Warning: Enum class for warning states.
    - OK: Enum class for ok states (no errors).
    - Expected: Enum class for expected states.
    - Success: Enum class for success states (glitching was successful).

    Example usage:

        from findus.GlitchState import GlitchState, OKType

        def return_ok():
            return GlitchState.OK.ack

        def main():
            response = return_ok()
            if issubclass(type(response), OKType):
                print("Response was OK.")
    """
    Error = _Error
    Warning = _Warning
    OK = _OK
    Expected = _Expected
    Success = _Success
