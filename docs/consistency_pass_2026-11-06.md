# Consistency pass, 6 November 2026

The same thing was described differently in the code, the docs, the two pitch decks, the scripts
and the front page. This pass made every place agree. The rule used:

- **Design and features:** the most advanced version wins, and the others are brought up to it.
  That is the ANVAYA 2k26 flagship (two processors, 4G VoLTE, a safety core that cannot be
  blocked).
- **Numbers:** the most recent computed result wins, not the highest number ever quoted. A number
  printed on 15 October is older, not more advanced, than one the current code produces.
- **Physics values:** a published source wins over an unsourced assumption (the team's own rule
  in `NOTES.md`).

Run `python tools/check_consistency.py` to see that it still holds: it rebuilds
`data/headline_numbers.json` from the results and reports any file that quotes a stale claim.

## 1. Physics: the improved front end's shield

| | Before | After |
|---|---|---|
| Watch ground to her body, improved input | 2 pF ("good shield"), no source | 35.4 pF unshielded × 23 % = 8.1 pF |
| Why | — | TI's best measured shield layout (ring + underside, larger than the electrode) leaves ~23 % [S14]; the same model already used 20–50 % for the active sweep (`sg_model.py`) |
| Watch sees of her body voltage, k | ~30 % | ~10 % |

One definition now lives in `sg_passive.py` (`CGB_UNSHIELDED`, `SHIELD_MID`, `SHIELD_BEST`) and is
reused by `fusion_study.py`, `whole_body.py`, `demo/sensor.js` and the explorer.

What it changed after re-running everything:

| Result | Before | After |
|---|---|---|
| Body voltage for 90 % of shoulder grabs (`fusion_study.py`) | 0.4 V | 1.6 V |
| Study, rule F2, body coverage at 1–100 V (`passive_stream.py`) | 74–76 % | 70–77 % |
| Study, rule F2, body coverage at 0.3 V | — | 53 % |
| Study, wrist grabs | 62–72 % | 68–74 % |
| Twin, rule F2 at ~10 V, wrist grabs | 88 % | 97 % |
| Twin, rule F2, 7 body places | 88 % | 90 % |
| Unwanted prompts | 0.22 / h (twin) | 0.22 / h (twin), unchanged |

Why the twin's wrist number went *up* while the static signal got smaller: in the model, his hand
on the strap adds to the same watch-to-body coupling. With only 2 pF, his hand changed the
pickup at the very moment of contact and smeared the charge step, so the onset step was missed in
most of the extra trials. With 8.1 pF his hand matters relatively less and the step stays clean.
This was traced trial by trial; it is a model effect that Gate 1 must confirm.

Part of the twin change was already there: re-running the 28 October code unchanged gives 89 %
over 7 places, not the 88 % that had been committed, so `demo/demo_check.json` was slightly stale
before this pass. The firmware changes below were checked trial by trial and change no detection
result.

Also regenerated: `data/event_stream_log.txt` (it still held the 12 October pre-3D run and
disagreed with `data/event_stream_results.json`, which reproduced exactly).

## 2. Firmware: Guard Mode rules (the flagship's "safety core")

`demo/firmware.js` is now described as the logic of the nRF5340 safety core (it said ESP32). The
flagship deck promises that nothing can block an alert, but the logic let anyone press "off". Now:

- Switching Guard Mode off needs her PIN; it cannot be switched off during a PIN prompt.
- A wrong PIN on the off screen starts the 15 s PIN prompt.
- The duress PIN on the off screen shows "Guard Mode off" but alerts silently and keeps guarding.
- After a duress PIN the watch does not prompt again (that would show the attacker a second prompt).
- An alert ends only with her PIN ("I'm safe" on the watch); her contacts are told.
- Strap removal is checked during the 5 s of learning too.
- Her own PINs (`setPins`): two different 4-digit codes; 1234 / 9999 are demo defaults only.

The demo page has the matching screens (PIN to turn off, "I'm safe" on the alert screen).
`node demo/test_firmware.js` runs 14 tests of these rules.

## 3. Architecture and spec

| Item | Was | Now (root: ANVAYA flagship) |
|---|---|---|
| Guard Mode processor | ESP32 (firmware header, design notes) | nRF5340 safety core on Zephyr; STM32U5 app processor; ESP32 only for the Gate 1 bench |
| Cellular | "4G LTE Cat-1" (BIH deck, design notes) | 4G VoLTE + GNSS, own SIM (a 112 voice call needs VoLTE) |
| Parts list | Single-ESP32 table | Full flagship table in `docs/design_notes.md` |

## 4. Numbers and claims in docs, decks and site

| Claim | Was (where) | Now |
|---|---|---|
| Grabs over 7 places | 70 % (BIH deck, ANVAYA deck, 3.5-min script) | 90 % twin; 70–77 % study |
| Struggles caught | 99 % (decks, script) | 100 % |
| Unwanted prompts | 0–1 in 9 h (decks, scripts) | 2 in 9 h |
| Wrist grabs | 99 % (BIH slide 7) | 97 % |
| Sources | 60 (decks, scripts), 15 (project map) | 72 |
| Sweep-only pipeline | 88–93 %, 4–5.5 prompts/h (README finding 6, 12 Oct) | 88 %, about 4 prompts/h |
| Price vs Apple Watch | "half the price" (ANVAYA script and notes) | ₹17,000 less (₹24,999 is ~60 % of ₹41,999) |
| Bench step table, k | about 30 % (whole-body docs) | about 10 % |

The BIH deck is updated by `tools/update_bih_deck.py` (text and the slide-7 bars). The ANVAYA
PPTX and PDF were re-exported from the HTML deck, which had also moved ahead of them before
this pass (its header and slide titles had changed).

## Not changed, on purpose

- **The two explainer videos** (`video/`) show the numbers of their day. Each README now says so;
  re-record before showing them.
- **"RV University, Mysuru"** in the decks and scripts. RV University's campus is on Mysuru Road
  in Bengaluru, so this may be a shortened address; it is the team's affiliation, so the team
  should decide.
- **No LICENSE was added.** The repo is public with no licence, which by default means all rights
  reserved. Choosing a licence is the team's decision, and should come after the patent question in
  the roadmap report.
- **The 99 % of the original proposal** in `docs/parameter_sources.md` and the README stays: it is
  quoted as Touché's grounded lab figure, which is correct.
