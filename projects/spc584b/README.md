# SPC584B JTAG password fault experiment

This experiment uses one persistent PyFtdi object to control the onboard
SPC584B-DISP FTDI directly. It does not launch a debugger daemon. The Python
code owns every JTAG state transition and implements the complete path used by
the campaign:

1. keep one external FTDI JTAG object open;
2. cold-cycle the target with its S1 switch or a serial relay in its 12 V DC input;
3. assert the FTDI-controlled external PORST signal and reset the main TAP;
4. require the exact raw IDCODE `0x20144041`;
5. select JTAGC instruction `0x07`;
6. arm the Pico edge trigger;
7. shift one uninterrupted 256-bit password scan;
8. enter core-2 OnCE with JTAGC instruction `0x2a`;
9. select OnCE Nexus3 access with 10-bit command `0x07c`;
10. read `PASS_LCSTAT` at `0xf7ff4000` three times through Nexus;
11. report access only when all reads are stable, valid, free of a Nexus bus
   error, and LCSTAT bit 30 (`JUN`) is set.

No CPU halt request, process-state cache, socket, or timeout is used as an
authorization result. The raw implementation is in `jtag_pyftdi.py`. The
campaign is in `spc584b_password_glitch.py`.

The board routes FTDI ACBUS1 (`SRST#_O`) through level shifter U23 to the
`USB_SRST#`/`RESET`/MCU `PORST` net. FTDI ACBUS5 is only U23's direction
control. The current transport drives ACBUS1 low, selects A-to-B direction on
ACBUS5 for 250 ms, releases the net by selecting B-to-A direction, and then
resets the TAP. Earlier revisions incorrectly treated ACBUS5 as the reset
output, so they did not assert PORST. Full cold cycles remain the authoritative
method for reproducing any access candidate.

A control run after the mapping correction passed without pressing SW1 or
cycling board power: IDCODE was `0x20144041`, the correct password set JUN, the
wrong password returned zero, and correct-password recovery set JUN again.
That result showed that ordinary transactions work with FTDI PORST, but a
subsequent immediate post-fault test showed that it is not sufficient evidence
of authoritative fault recovery.

The code never writes flash, UTEST, DCF, lifecycle, or OTP.

## Wiring

- Pico `GND` to target `GND`
- Pico `TRIGGER` input to JTAG `TCK`
- Pico `GLITCH` SMA center to the VDD_LV pad of C43
- Pico `GLITCH` SMA shield to the GND pad of C43
- Pico `RESET` and `VTARGET` disconnected
- Board powered by its normal 12 V wall adapter, with an isolated serial-relay
  contact wired in series with one conductor of the low-voltage 12 V DC lead
- Board's onboard FTDI connected over USB

Switch only the low-voltage DC lead. Do not put the relay or any Pico Glitcher
connection on AC mains. The SPC584B-DISP input is 12 V, while Pico Glitcher v3
offers target rails only up to 5 V, so do not connect the board's 12 V input to
Pico `VTARGET` or `VCC_EXTERN`. Keep USB attached to the onboard FTDI so the
same PyFtdi object survives target power cycles.

C43 is a capacitor, not a resistor. On the stock discovery board it is 2.2 uF
between VDD_LV and GND. Verify the VDD_LV pad by continuity to TP8 and verify
the other pad by continuity to ground with power removed. C35 through C48 put
about 4.8 uF of listed capacitance on that rail, and Q1 actively supplies it
while the board is powered. A long pulse may therefore be a broad brownout or
reset rather than a fault in the password comparison.

## Install

```bash
cd /Users/brandon/Desktop/mpc/fault-injection-library
python3 -m venv .venv
.venv/bin/pip install -e .
chmod 600 /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin
```

The project pins PyFtdi, PyUSB, and a packaged libusb runtime. No system daemon
or external debugger executable is required.

## Mandatory power-cycle test

The no-solder method uses the board's existing S1 power switch. Keep the wall
adapter and onboard FTDI USB connected, then run:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode power-cycle-test \
  --manual-power-cycle \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin
```

Follow each prompt by switching S1 to the stated position before pressing
Enter. The script waits 1.5 seconds while off and 4 seconds after power-on.
The test must show the
expected IDCODE while on, a different or unreadable IDCODE while off, the
expected IDCODE after restoration, and `POWER_CYCLE_TEST_PASS`. Campaign modes
also repeat this physical proof at startup. AT-command and LCUS-1 USB relays
can automate it through `--power-relay-port`.

The detected SMAKN LCUS-1 appears on this Mac as `/dev/cu.usbserial-110`. Its
normally-open dry contacts switch the 12 V feed; the relay's USB connection
only powers and controls the relay. With the bench supply output off, wire:

- bench-supply positive to relay `COM`;
- relay `NO` to the positive terminal of a 5.5 x 2.1 mm male barrel-plug adapter;
- bench-supply negative directly to the adapter's negative terminal;
- the barrel plug to board connector X5, with board switch S1 left on.

Use the markings on the relay PCB to identify `COM` and `NO`; do not infer the
terminal order from the product photograph. Set the bench supply to 12.0 V
with an initial 0.5 A current limit and verify the barrel polarity matches the
original adapter before enabling its output. Then validate automated cold
cycling:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode power-cycle-test \
  --power-relay-port /dev/cu.usbserial-110 \
  --relay-protocol lcus \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin
```

For LCUS-1, the script defaults to binary state 1 for on and state 0 for off.
The run must show IDCODE `0x20144041` with power on, an unreadable IDCODE with
power off, restoration of `0x20144041`, and `POWER_CYCLE_TEST_PASS` before the
relay is used in a campaign.

The bench acceptance run on 2026-09-12 passed. With S1 on, raw IDCODE was
`0x20144041`; with S1 off, it became `0xffffffff`; and after S1 was restored it
returned to `0x20144041`. Three separately cold-booted controls then produced
correct-password `ACCESS_JUN_SET`, one-bit-wrong-password zero LCSTAT/RWCS
data with `JUN=0`, and correct-password recovery `ACCESS_JUN_SET`. This proves
the manual switch supplies a reliable full reset. A later schematic audit
found that the earlier FTDI implementation had not actually driven PORST, so
those results do not establish whether correctly asserted PORST can replace a
full power cycle.

Do not power the SPC584B-DISP through Pico's 5 V output. The board input expects
12 V, direct injection into its internal 5 V net would backfeed the buck
converter, and Pico is not sized to power the complete discovery board.

## Raw-JTAG controls

Run this before another glitch attempt:

```bash
cd /Users/brandon/Desktop/mpc/fault-injection-library

.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode controls \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin
```

This does not initialize or fire the Pico. It must show all of the following:

```text
RAW_IDCODE=0x20144041
CONTROL password=correct result=ACCESS_JUN_SET
CONTROL password=wrong result=<anything other than ACCESS_JUN_SET>
CONTROL password=correct_recovery result=ACCESS_JUN_SET
EXPERIMENT_RESULT=CONTROLS_PASS
```

The correct control proves the password word order, OnCE route, Nexus
transactions, target byte order, LCSTAT address, and JUN mask through the raw
Python implementation. The wrong control proves that reset re-arms security
and that one changed password bit does not set JUN. The final
correct-password control proves recovery from that denied state in the same
persistent PyFtdi session. A campaign must not run if any control fails.

The initial hardware acceptance run on 2026-09-12 returned raw IDCODE
`0x20144041`; three correct-password reads of `LCSTAT=0xe0000002` with
`RWCS=0x10c00005`, stable data, `JUN=1`, and no transport error; and three
wrong-password reads of zero with `JUN=0` and no transport error. This validates
the direct positive and negative oracle. The following correct-password
recovery in the same persistent session again returned three stable
`LCSTAT=0xe0000002` reads with `RWCS=0x10c00005`, `JUN=1`, and no transport
error. The complete raw harness acceptance sequence therefore passes.

## Electrical response measurements

The raw 20 us authority run on 2026-09-12 changed all five correct-password
shots from valid LCSTAT data to stable all-ones LCSTAT/RWCS data. Every shot
then recovered to three stable `LCSTAT=0xe0000002` reads with `JUN=1`. This
passes the digital authority gate: the connected low-power crowbar reproducibly
affects the target/JTAG path and the effect is recoverable. It does not identify
the mechanism; at this width a broad brownout or reset remains the likely
explanation.

At the other endpoint, five raw shots at edge 260, delay 0 ns, and width 8 ns
all returned three stable `LCSTAT=0xe0000002` reads with `JUN=1`. The 8 ns pulse
therefore had no detectable effect. The measured transition lies somewhere
between 8 ns and 20 us at this edge and delay.

A subsequent coarse sweep tested widths from 1 us through 20 us in 1 us steps
with three repetitions per cell. The 1 us cell passed 3/3. Every cell from
2 us through 20 us produced stable all-ones LCSTAT/RWCS data 3/3 and recovered
with the correct password. The coarse transition is therefore between 1 us and
2 us; the uniform behavior above 2 us continues to look like rail collapse.

A temporal control then applied the same 2 us pulse 100 us after the final
password edge. All five shots still produced stable all-ones LCSTAT/RWCS data
and all five recovered. The 2 us failure is therefore independent of password
comparison timing and is excluded as a bypass signal. It establishes only a
generic target or JTAG-path collapse threshold.

Those observations intended to use DCI plus nTRST/nSRST between attempts, but
a later schematic audit found that the raw FTDI mapping did not assert PORST:
ACBUS5 was driven as though it were reset data even though it controls U23's
direction, while the actual ACBUS1 `SRST#_O` pin was never driven. At attempt
28, a 1.4 us shot returned zero LCSTAT/RWCS data and the immediate
correct-password recovery also returned zero. The next process then failed its
unglitched correct-password control in the same way. This is evidence of the
incomplete pre-fix reset path, not an authentication result. Do not use that
partial CSV to claim a 1.4-2.0 us boundary.

The manual cold-cycle endpoint map then repeated the measurement with a full
S1 cycle before every shot. At edge 260 and delay 0, 1 us passed 2/2 with
stable `LCSTAT=0xe0000002` and `JUN=1`; 2 us produced invalid all-ones
LCSTAT/RWCS data 2/2, and both failures recovered after another cold cycle.
This validates the 1-2 us electrical disruption bracket under the corrected
reset method. The post-authentication control above still excludes the 2 us
response as evidence of a password-comparison bypass.

Successive three-shot authority tests then narrowed the transition using a
full manual cold boot before every shot. Widths 1.5 us, 1.752 us, 1.876 us,
and 1.908 us all produced stable `LCSTAT=0xe0000002`, `RWCS=0x10c00005`, and
`JUN=1`. Widths 1.940 us, 1.924 us, 1.916 us, and 1.912 us all produced
recoverable invalid all-ones LCSTAT/RWCS samples. At edge 260 and delay 0,
the boundary is therefore located at the Pico's adjacent 4 ns timing ticks:
1.908 us passes and 1.912 us disrupts. This remains an electrical-effect
boundary; it is not evidence that an incorrect password can set JUN.

The recorded command was:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode sensitivity-map \
  --rpico /dev/cu.usbmodem1301 \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin \
  --edge-count 260 \
  --delay 0 0 \
  --length 20000 20000 \
  --repeats 5 \
  --strict-oracle \
  --output projects/spc584b/run-artifacts/raw-authority-lp-20us-repeat5.csv
```

For every shot, strict mode performs one full cold cycle, requires the expected
IDCODE, then arms the Pico and starts the password scan. After every changed
result it cold-cycles again and requires the correct password to restore stable
`LCSTAT.JUN=1`. This distinguishes a
recoverable electrical effect from persistent harness failure. It still does
not show whether the target brownouted or whether the password comparison was
disturbed.

## Sensitivity map

At 1 MHz JTAG, edge 260 is the computed `Update-DR` neighborhood for the raw
256-bit scan. Without a scope, first reduce pulse width until the correct
password has both passing and changed cells. Record every attempt in a new CSV.
Do not scan a 4 ns lattice through the full 20 us interval; narrow the width
range with successive authority tests.

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode sensitivity-map \
  --rpico /dev/cu.usbmodem1301 \
  --manual-power-cycle \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin \
  --edge-count 260 \
  --delay MIN_DELAY_NS MAX_DELAY_NS \
  --length MIN_LENGTH_NS MAX_LENGTH_NS \
  --step-ns 4 \
  --repeats 5 \
  --strict-oracle \
  --output projects/spc584b/run-artifacts/raw-edge260-sensitivity.csv
```

The `SENSITIVITY_BOUNDARY` lines identify changed cells directly adjacent to
cells where the correct password still sets JUN.

After the power-cycle test passes, rerun the interrupted narrow map into a new
file:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode sensitivity-map \
  --rpico /dev/cu.usbmodem1301 \
  --manual-power-cycle \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin \
  --edge-count 260 \
  --delay 0 0 \
  --length 1000 2000 \
  --step-ns 100 \
  --repeats 5 \
  --strict-oracle \
  --output projects/spc584b/run-artifacts/raw-edge260-width-100ns-coldcycle.csv
```

## Attack

Only after locating a repeatable correct-password boundary should the script
submit the one-bit-wrong password in the same timing region:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode attack \
  --rpico /dev/cu.usbmodem1301 \
  --manual-power-cycle \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin \
  --edge-count 260 \
  --delay MIN_DELAY_NS MAX_DELAY_NS \
  --length MIN_LENGTH_NS MAX_LENGTH_NS \
  --strict-oracle
```

For exploratory batches without repeated manual S1 prompts, attack mode can
use the FTDI-controlled external PORST signal. Strict mode proves a locked
state before each shot and correct-password recovery after every denial. The
run aborts instead of continuing if either gate fails:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode attack \
  --reset-only-attack \
  --rpico /dev/cu.usbmodem1301 \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin \
  --edge-count 260 \
  --delay 0 0 \
  --length 1908 1908 \
  --repeats 10 \
  --attempts 10 \
  --strict-oracle
```

This batch mode avoids routine power-switch operation. It asserts PORST for
250 ms using ACBUS1 as reset data and ACBUS5 as the level-shifter direction.
A recovery failure still requires one full power cycle before another run,
and any access candidate must be reproduced with the full cold-cycle method.

The following reset-only results were collected before the ACBUS1/ACBUS5 PORST
mapping was corrected and describe the former DCI/TAP reset path. The first
batch used the one-bit-wrong password at edge 260,
delay 0, and width 1.908 us. All ten pre-shot gates showed the expected locked
zero LCSTAT/RWCS data. All ten shots returned invalid all-ones data, and all
ten DCI-reset correct-password recoveries restored stable `JUN=1`. The batch
therefore found no access and demonstrated that 1.908 us is already disruptive
under the reset-only attack conditions. Because both the password and reset
regime differ from the cold-cycle correct-password map, this does not establish
which difference moved the observed boundary.

At 1.876 us, a second reset-only wrong-password batch produced the ordinary
locked zero LCSTAT/RWCS response 3/3, with all pre-shot gates and
correct-password recoveries passing. The reset-only wrong-password transition
at edge 260 and delay 0 is therefore bracketed between 1.876 and 1.908 us.
At the 1.892 us midpoint, two of three shots returned invalid all-ones data and
one returned the ordinary locked zero response. Every recovery passed and no
shot set JUN. This is a mixed disruption boundary, so repeated sampling at the
same point is required before refining nearby timings.

A planned 20-shot repeat at 1.892 us then stopped after attempt 9 when strict
correct-password recovery failed. Of the ten completed shots, seven returned
invalid all-ones data and three returned the ordinary locked zero response;
none set JUN. The first nine recoveries passed, while the tenth remained at
zero after the pre-fix DCI/TAP reset. This proves the abort guard and the
former reset path's limitation; it does not characterize the corrected PORST
implementation.

The first attack using corrected 250 ms FTDI PORST stopped after one 1.908 us
shot. Its pre-shot locked gate passed and the shot returned the ordinary
zero-valued denial, but the following PORST, IDCODE gate, and correct-password
submission still returned zero. Thus PORST restored a readable main TAP but
did not restore authorization behavior after this fault. No access was
observed. Longer PORST assertion and physical LD4 reset indication must be
checked before relying on this path; otherwise a full power cycle remains
necessary.

A follow-up control run increased the requested FTDI PORST hold from 250 ms to
1000 ms while the target remained in that post-fault state. IDCODE remained
healthy at `0x20144041`, but the first correct-password control still returned
three zero LCSTAT/RWCS samples with `JUN=0`. Longer reset assertion alone did
not restore that state. After a full S1 power cycle, the same 1000 ms control
run visibly asserted LD4 and passed correct/wrong/correct. This proves that the
FTDI signal reaches the board RESET/PORST net and that PORST handles ordinary
password-state rearming, while the observed faulted state still required a
full power cycle.

A fresh reset-only attack then used 1000 ms PORST holds and randomized widths
from 1.876 through 1.904 us. Widths 1.904 and 1.880 us produced ordinary
zero-valued denial and passed correct-password recovery. The next shot at
1.900 us also produced ordinary denial, but the following correct-password
submission remained at zero after PORST, so the strict guard stopped after
three attempts. No access was observed. Post-fault PORST recovery is therefore
not deterministic near this timing region, even when the immediate oracle is
the ordinary zero-valued denial rather than invalid all-ones data.

An `ACCESS_CANDIDATE` requires three stable direct reads with LCSTAT.JUN set.
The script stops without applying another reset so the authorization state can
be checked independently. Exit codes are 0 for no candidate, 10 for an access
candidate, 2 for an experimental error, and 130 for interruption.

## Edge mapping with a scope

With the glitch output physically disconnected from the target rail:

```bash
.venv/bin/python projects/spc584b/spc584b_password_glitch.py \
  --mode edge-map \
  --rpico /dev/cu.usbmodem1301 \
  --password-file /Users/brandon/Desktop/mpc/spc584b-jtag-password.bin \
  --edge-range 252 264 \
  --confirm-glitch-disconnected
```

Use TCK and the marker output to identify the final password-scan clocks. The
Pico PIO counts the externally generated TCK waveform in hardware.
