# Her own hand, the transmit check and skin response (28 October 2026)

Four effects the fused watch (rule F, `docs/whole_body_fusion.md`) did not model yet, now added at
the team's request. Code: `sg_newch.py` (physics), `sg_passive.py` and `passive_stream.py`
(study), `demo/sensor.js` and `demo/firmware.js` (digital twin). Figure: `figures/fig19_transmit_check.png`.
Numbers: `data/transmit_results.json`, `data/passive_stream_results.json`, `demo/demo_check.json`.
Sources S61–S72 are logged in `docs/SparshaGuard_paper_values.xlsx` (status "In model (28 Oct 2026)").

## 1. Her own hand on the watch changes what the static channel sees

The static channel reads a fixed part k of her body voltage, k = C_GE / (C_GE + C_GB + C_in).
When she touches the glass, her finger (0.5–1.5 cm²) or palm (4–12 cm²) couples her body to the
watch ground through the display stack (1.5–3 mm, εr 3–7), adding 1–30 pF to C_GB. So k drops
in a few milliseconds while no charge moves: a step that looks like a contact.

A tap takes about 133 ms [S72], so the finger lands at about 0.1–0.3 m/s and the coupling rises
over a few ms as the gap closes. Most of these steps are already rejected because her hand is
moving before it lands ("already moving" check), but not all.

## 2. Skin-stretch noise under a dry electrode

Forearm skin carries about 15 mV across its outer layer; stretching it changes that voltage and
shows up under a dry electrode as a motion artefact [S67]. Each arm jerk now adds a 0.3–3 mV bump
and walking adds 0.05–0.5 mV of arm-swing ripple. The contact-step detector already needed 6× the
noise in one sample, so these did not add false steps.

## 3. The transmit check (and why shunt mode does not work)

**Transmit (loading) mode** [S70]: the steel back sends a small 100 kHz, 0.5 V signal into her
skin and the watch measures the current. Her own hand over the watch adds C_hand between her body
and the watch ground, so the current jumps (by 26–130 %) at the same instant as the static step. A
stranger touching her anywhere but the watch leaves it flat: the earth around a floating watch
sits at her own potential, so his body adds almost nothing.

**Own-hand veto** in the firmware: a person-like static step is reclassed as *her own hand* when
the transmit current jumps by 2 % or more at the same moment *and* the size of the static step
matches the change in k that the jump predicts (within 25 % + 6× noise). The firmware knows the
ratio between the two from a one-off calibration (±20 % error assumed).

**Shunt mode** (a receive pad on the strap whose signal *drops* when a grounded hand blocks it,
as in DiamondTouch [S71]) was checked with a nodal circuit study at 100 kHz and rejected. On a
floating watch, the stranger is not "grounded" relative to the watch, and his hand *raises* the
received signal just like hers:

| Case | Receive signal (×) | Transmit current (×) |
|---|---|---|
| Her hand on the glass | 0.99 | 1.60 |
| Her hand on the strap | 37 | 15.8 |
| Stranger, hand on the strap only | 7.0 | 3.4 |
| Stranger grabs wrist skin + strap | 39 | 16.5 |
| Stranger grabs forearm | 1.02 | 1.01 |
| Stranger grabs shoulder | 1.00 | 1.00 |
| Metal pole on the strap | 8.8 | 4.2 |

(Medians over the geometry ranges; full ranges in `data/transmit_results.json`.) Her hand on the
strap and a stranger's grab look the same, so neither mode can tell *who* is touching. The
transmit check is only used for what it can do: confirm that a step came from her hand on the
glass.

**Safety:** the baseline current is about 7.4 µA, under the 100 µA patient auxiliary current that
IEC 60601-1 allows (type B/BF, normal condition) [S69].

## 4. Skin response (EDA): catching a grab that only holds her

About 70 % of women assaulted report freezing (tonic immobility) [S68]. A grab that holds her
without pulling was missed by rule F away from the wrist, because the anywhere path needed her arm
to be pulled. Two pads on a split case back now read skin conductance (8 samples per second in the
study, 5 per second in the twin).

| Value | Used | Source |
|---|---|---|
| Response onset after the stimulus | 1–3 s | [S61] |
| Rise time | 1–3 s | [S61] |
| Half-recovery | 2–10 s | [S61] |
| Spontaneous responses at rest | 1–5 per minute (×1.5 while walking) | [S62] |
| First response to a startle | 1.56 µS median (finger) | [S63] |
| Wrist versus finger | 0.2–0.6 × | [S64, S65] + estimate |
| Grab → fear response | probability 0.9 | estimate |
| Brush by a stranger → orienting response | probability 0.3, 0.3 µS median | estimate |
| Friend holding her wrist | probability 0.2 | estimate |
| Pad-pressure artefacts during arm jerks | 0.05–0.5 µS, fast | estimate |

The firmware counts a skin response when, 0.8–4.5 s after a person step, conductance rises by
0.45 µS or more, more slowly than 1 µS/s, over at least 0.5 s and with no arm jerk at the time
(rule structure as Kleckner [S66]). A threshold of 0.3 µS let brushes on a bus through.

## The new rule F2

- *Wrist path:* the active sweep held 2 s AND a person step within 4 s before (her own hand
  excluded by the transmit check).
- *Anywhere path:* a person step AND (her arm pulled within 3 s OR a skin response 0.8–4.5 s later).

A "transmit rescue" (accept the wrist hold when the transmit current jumped although no static
step was found) was tried and dropped: it added about 6 points of wrist grabs at 10 V for about
0.5 more unwanted prompts per hour while walking.

## Results

**Study** (`passive_stream.py`; improved input + ADS1115; 40 grabs per place and voltage, 6 h of
walking, bus and desk life per setting; fig 17, 18; `data/passive_stream_results.json`):

| Body voltage | Body coverage, F | Body coverage, F2 | Wrist, F / F2 | Other places, F | Other places, F2 | Unwanted prompts/h, F / F2 |
|---|---|---|---|---|---|---|
| 1 V | 60 % | 74 % | 68 % / 62 % | 56–66 % | 71–79 % | 0.28 / 0.28 |
| 10 V | 62 % | 75 % | 68 % / 68 % | 59–65 % | 74–80 % | 0.11 / 0.11 |
| 100 V | 60 % | 76 % | 72 % / 72 % | 53–68 % | 73–83 % | 0.06 / 0.11 |

Rule A (today's sweep only) covers 12–13 % of the body at 4–5 unwanted prompts per hour.
Unwanted prompts exclude a friend holding her wrist (the PIN is the right answer there).
Across 0.3–100 V, F2 covers 69–76 % of the body against 58–62 % for F, at the same 0.1–0.4
prompts per hour. With today's input and the ESP32 ADC, F2 needs 10 V or more (64 % at 10 V,
9 % at 1 V).

Both rules catch fewer wrist grabs than in the 14 October study (83–88 % then): a grabber's palm
now covers her watch face in 30 % of wrist grabs, which shrinks the static step, and skin-stretch
noise is added. At 1 V the own-hand veto also wrongly vetoes a few of those palm-over-face grabs
(62 % against 68 %). The transmit check on its own (F2-tx, F2 without the skin path) gives the
same coverage as F; its value is that her own hand never prompts.

**Digital twin** (`node demo/check_demo.js`, bodies at ~10 V): F2 catches 88 % of grabs over
7 places (F: 70 %), 62–65 % of grabs that only hold her (F: 0 %), her own palm on the watch never
prompts (F: 2.5 %), and unwanted prompts stay at 0.22 per hour.

## What is still unknown

- **Skin response on the wrist during a real grab.** The fear amplitudes come from finger and palm
  recordings in the lab [S63]; the wrist factor (0.2–0.6) and the 0.9 response probability are
  estimates. A person who freezes may still respond strongly, but Gate 1 must check it.
- **Brushes in a crowd.** How often a stranger's brush raises her skin conductance by 0.45 µS on
  the wrist is not published; the 0.3 probability is an estimate and sets most of F2's extra
  prompts.
- **Display stack and calibration.** The transmit-to-k ratio depends on the real display stack;
  the ±20 % calibration error assumed here should be measured.
