"""Raw PyFtdi JTAG transport for the SPC584B-DISP onboard FTDI.

It implements the small set of JTAGC, OnCE, and Nexus transactions used by the
password fault experiment directly on top of PyFtdi.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

import libusb_package
from pyftdi.bits import BitSequence
from pyftdi.ftdi import Ftdi
from pyftdi.jtag import JtagEngine
import usb.backend.libusb1
import usb.core
import usb.util


USB_VID = 0x263D
USB_PID = 0x4001
USB_INTERFACE = 1  # FTDI channel 0 / interface index 1 in libusb
FTDI_HIGH_TRST_OUT = 1 << 0  # ACBUS0 / TRST#_O
FTDI_HIGH_SRST_OUT = 1 << 1  # ACBUS1 / SRST#_O
FTDI_HIGH_SRST_DIR = 1 << 5  # ACBUS5 / SRST#_DIR

JTAGC_IR_LENGTH = 6
IR_IDCODE = 0x01
IR_PASSWORD = 0x07
IR_ACCESS_CORE_2 = 0x2A

ONCE_IR_LENGTH = 10
ONCE_NEXUS3 = 0x07C
ONCE_NONE = 0x011

NEXUS_RWCS = 0x07
NEXUS_RWA = 0x09
NEXUS_RWD = 0x0A
NEXUS_RWCS_ERROR = 1 << 1
NEXUS_READ_WORD = (1 << 31) | (2 << 27) | (3 << 22) | (1 << 2)

EXPECTED_IDCODE = 0x20144041
PASS_LCSTAT = 0xF7FF4000
LCSTAT_JUN = 1 << 30


class JtagError(RuntimeError):
    """A raw transport or target response failed validation."""


@dataclass(frozen=True)
class AccessProbe:
    state: str
    lcstats: tuple[int, ...]
    rwcs: tuple[int, ...]
    error: str = ""

    @property
    def access_observed(self) -> bool:
        return self.state == "ACCESS_JUN_SET"

    @property
    def detail(self) -> str:
        values = ",".join(f"0x{value:08x}" for value in self.lcstats)
        statuses = ",".join(f"0x{value:08x}" for value in self.rwcs)
        stable = bool(self.lcstats) and len(set(self.lcstats)) == 1
        valid = (
            bool(self.lcstats)
            and all(value not in (0, 0xFFFFFFFF) for value in self.lcstats)
            and not any(value & NEXUS_RWCS_ERROR for value in self.rwcs)
        )
        jun = stable and valid and bool(self.lcstats[0] & LCSTAT_JUN)
        return (
            f"lcstats={values or 'none'};rwcs={statuses or 'none'};"
            f"stable={int(stable)};valid={int(valid)};jun={int(jun)};"
            f"transport_error={self.error or 'none'}"
        )


class SPC584BJtag:
    """Persistent raw-JTAG controller for one SPC584B-DISP board."""

    def __init__(
        self,
        frequency_hz: int = 1_000_000,
        serial: str | None = None,
        power_cycle: Callable[[], None] | None = None,
    ):
        self.frequency_hz = frequency_hz
        self.serial = serial
        self.power_cycle = power_cycle
        self.engine: JtagEngine | None = None
        self.device = None
        self._in_once = False

    @staticmethod
    def _usb_backend():
        return usb.backend.libusb1.get_backend(
            find_library=lambda _: libusb_package.find_library("libusb-1.0")
        )

    def _find_device(self):
        devices = list(
            usb.core.find(
                find_all=True,
                idVendor=USB_VID,
                idProduct=USB_PID,
                backend=self._usb_backend(),
            )
        )
        if self.serial is not None:
            devices = [
                device
                for device in devices
                if usb.util.get_string(device, device.iSerialNumber) == self.serial
            ]
        if not devices:
            qualifier = f" serial {self.serial}" if self.serial else ""
            raise JtagError(
                f"SPC584B-DISP FTDI {USB_VID:04x}:{USB_PID:04x}{qualifier} not found"
            )
        if len(devices) != 1:
            raise JtagError(
                "multiple SPC584B-DISP FTDI devices found; select one with --ftdi-serial"
            )
        return devices[0]

    def open(self) -> "SPC584BJtag":
        if self.engine is not None:
            return self
        self.device = self._find_device()
        engine = JtagEngine(trst=False, frequency=self.frequency_hz)
        controller = engine.controller
        controller._frequency = self.frequency_hz
        try:
            controller._ftdi.open_mpsse_from_device(
                self.device,
                interface=USB_INTERFACE,
                direction=controller.direction,
                frequency=self.frequency_hz,
                latency=1,
            )
            controller._ftdi.write_data(
                bytearray((Ftdi.SET_BITS_LOW, 0x00, controller.direction))
            )
            controller._ftdi.set_latency_timer(1)
            self.engine = engine
            # A previous process may have closed while an auxiliary OnCE TAP
            # owned the chain. Hardware reset both target-facing reset lines so
            # a new process always starts from the main JTAGC TAP.
            self.reset_lines_and_tap(hold_ms=250)
            return self
        except Exception:
            try:
                engine.close()
            finally:
                self.engine = None
                if self.device is not None:
                    usb.util.dispose_resources(self.device)
                self.device = None
            raise

    def close(self) -> None:
        if self.engine is not None:
            try:
                try:
                    self.release_once()
                    self._set_reset_lines(
                        trst_asserted=False,
                        srst_asserted=False,
                    )
                    self.engine.sync()
                except Exception:
                    # A configured cold cycle recovers the target before the
                    # next transaction even if best-effort cleanup fails.
                    pass
                self.engine.close()
            finally:
                self.engine = None
        if self.device is not None:
            try:
                usb.util.dispose_resources(self.device)
            finally:
                self.device = None
        self._in_once = False

    def __enter__(self) -> "SPC584BJtag":
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

    def _require_engine(self) -> JtagEngine:
        if self.engine is None:
            raise JtagError("FTDI JTAG controller is not open")
        return self.engine

    def tap_reset(self) -> None:
        self._require_engine().reset()
        self._require_engine().sync()
        self._in_once = False

    def _set_reset_lines(self, *, trst_asserted: bool, srst_asserted: bool) -> None:
        """Drive nTRST and the board RESET/PORST net through the FTDI."""
        engine = self._require_engine()
        value = 0 if trst_asserted else FTDI_HIGH_TRST_OUT
        direction = FTDI_HIGH_TRST_OUT | FTDI_HIGH_SRST_DIR

        # U23 is an SN74LVC1T45 between FTDI ACBUS1 (SRST#_O) and the target's
        # USB_SRST#/RESET/PORST net. ACBUS5 is SRST#_DIR: high selects A->B and
        # low selects B->A. To assert reset, make ACBUS1 an output-low and set
        # ACBUS5 high. To release it, make ACBUS1 an input and set ACBUS5 low;
        # this avoids driving high against the board's open-drain reset sources.
        if srst_asserted:
            direction |= FTDI_HIGH_SRST_OUT
            value |= FTDI_HIGH_SRST_DIR
        engine.controller.ftdi.write_data(
            bytearray((Ftdi.SET_BITS_HIGH, value, direction))
        )

    def reset_lines_and_tap(self, hold_ms: int = 250) -> None:
        """Assert external PORST through the FTDI, release it, then reset TAP."""
        self._set_reset_lines(trst_asserted=True, srst_asserted=True)
        time.sleep(hold_ms / 1000)
        self._set_reset_lines(trst_asserted=False, srst_asserted=False)
        time.sleep(hold_ms / 1000)
        self.tap_reset()

    def _ir(self, value: int, length: int = JTAGC_IR_LENGTH) -> None:
        self._require_engine().write_ir(BitSequence(value, length=length))

    def _dr_write(self, value: int, length: int) -> None:
        engine = self._require_engine()
        engine.write_dr(BitSequence(value, length=length))
        engine.sync()

    def _dr_read(self, length: int) -> int:
        return int(self._require_engine().read_dr(length))

    def read_idcode(self, reset: bool = True) -> int:
        if reset:
            self.tap_reset()
        self._ir(IR_IDCODE)
        return self._dr_read(32) & 0xFFFFFFFF

    def require_idcode(self) -> int:
        observed = self.read_idcode()
        if observed != EXPECTED_IDCODE:
            raise JtagError(
                f"IDCODE 0x{observed:08x} does not match 0x{EXPECTED_IDCODE:08x}"
            )
        return observed

    def destructive_reset(self, hold_ms: int = 250) -> None:
        """Cold-cycle when configured; otherwise assert external PORST."""
        if self._in_once:
            self.release_once()
        if self.power_cycle is not None:
            self.power_cycle()
            self.reset_lines_and_tap(hold_ms=100)
            return
        self.reset_lines_and_tap(hold_ms=hold_ms)

    @staticmethod
    def password_wire_value(words: tuple[int, ...]) -> int:
        """Pack eight sequential 32-bit fields into LSB-first wire order."""
        if len(words) != 8:
            raise ValueError("JTAG password must contain eight 32-bit words")
        if any(word < 0 or word > 0xFFFFFFFF for word in words):
            raise ValueError("JTAG password words must be unsigned 32-bit values")
        return sum(word << (32 * index) for index, word in enumerate(words))

    def select_password_register(self) -> None:
        self.tap_reset()
        self._ir(IR_PASSWORD)
        # The Pico is armed only after this method returns. Flush the IR scan so
        # its TCK edges cannot contaminate the password-DR edge count.
        self._require_engine().sync()

    def submit_password_words(self, words: tuple[int, ...]) -> None:
        self._dr_write(self.password_wire_value(words), 256)

    def _once_command(self, command: int) -> None:
        self._ir(command, ONCE_IR_LENGTH)

    def enter_nexus(self) -> None:
        self._ir(IR_ACCESS_CORE_2, JTAGC_IR_LENGTH)
        self._once_command(ONCE_NEXUS3)
        self._in_once = True

    def _nexus_write_register(self, register: int, value: int) -> None:
        self._dr_write((register << 1) | 1, 8)
        self._dr_write(value & 0xFFFFFFFF, 32)

    def _nexus_read_register(self, register: int) -> int:
        self._dr_write(register << 1, 8)
        return self._dr_read(32) & 0xFFFFFFFF

    @staticmethod
    def _target_word(raw: int) -> int:
        return int.from_bytes(raw.to_bytes(4, "little"), "big")

    def nexus_read_word(self, address: int) -> tuple[int, int]:
        """Return one big-endian target word and its Nexus RWCS status."""
        if not self._in_once:
            self.enter_nexus()
        self._nexus_write_register(NEXUS_RWA, address)
        self._once_command(ONCE_NEXUS3)
        self._nexus_write_register(NEXUS_RWCS, NEXUS_READ_WORD)
        self._once_command(ONCE_NEXUS3)
        raw = self._nexus_read_register(NEXUS_RWD)
        rwcs = self._nexus_read_register(NEXUS_RWCS)
        return self._target_word(raw), rwcs

    def probe_access(self, samples: int = 3) -> AccessProbe:
        """Classify access from direct LCSTAT reads; never requests a CPU halt."""
        values: list[int] = []
        statuses: list[int] = []
        try:
            self.enter_nexus()
            for _ in range(samples):
                value, status = self.nexus_read_word(PASS_LCSTAT)
                values.append(value)
                statuses.append(status)
        except Exception as error:
            return AccessProbe(
                "ORACLE_ERROR",
                tuple(values),
                tuple(statuses),
                f"{type(error).__name__}: {error}",
            )

        stable = len(set(values)) == 1
        valid = all(value not in (0, 0xFFFFFFFF) for value in values)
        no_bus_error = not any(status & NEXUS_RWCS_ERROR for status in statuses)
        if not stable:
            state = "ACCESS_LCSTAT_UNSTABLE"
        elif not valid or not no_bus_error:
            state = "NO_VALID_LCSTAT"
        elif values[0] & LCSTAT_JUN:
            state = "ACCESS_JUN_SET"
        else:
            state = "ACCESS_JUN_CLEAR"
        return AccessProbe(state, tuple(values), tuple(statuses))

    def release_once(self) -> None:
        """Return ownership from the OnCE auxiliary TAP to the main JTAGC TAP."""
        if not self._in_once:
            return
        engine = self._require_engine()
        self._once_command(ONCE_NONE)
        engine.change_state("shift_dr")
        engine.controller.write(BitSequence(0, length=32))
        engine.change_state("pause_dr")
        # pause_dr -> exit2_dr -> update_dr -> run_test_idle releases OnCE.
        engine.change_state("run_test_idle")
        engine.sync()
        self._in_once = False
