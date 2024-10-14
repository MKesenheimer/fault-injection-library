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
    default = 0

class _Error(ErrorType):
    default = 0

class _Warning(WarningType):
    default = 0

class _OK(OKType):
    default = 0

class _Success(SuccessType):
    default = 0

class GlitchState():
    Expected = _Expected
    Error = _Error
    Warning = _Warning
    OK = _OK
    Success = _Success