# Covering more of her body with fewer false alarms (fusion study, 14 October 2026)

Goal set by the team: maximise how much of her body a grab is detected on, while keeping
unwanted PIN prompts low. Script: `fusion_study.py`. Figures: `figures/fig15_fusion_voltage.png`,
`figures/fig16_fusion_locations.png`. Numbers: `data/fusion_results.json`. New paper values are
in `docs/SparshaGuard_paper_values.xlsx`, tagged "Fusion study (doc)" or "Accuracy benchmark".
`sg_model.py` (the active sweep) is unchanged; the demo and explorer now include the passive channel (see the last section).

## What was added

A **passive static-charge channel** on the same wrist electrode. People carry static charge, so
two bodies are almost never at the same voltage. When another person touches her anywhere, the
two bodies share charge and her whole body's voltage jumps in under a millisecond; the floating
watch sees a fixed part of that jump (6 % with today's input, about 30 % with a bootstrapped
input and good shield).

Physics used, with sources: body capacitance 110–250 pF (Jonassen [S4]); fabric as a series
capacitor (Ng & Reaz [S7], hand area [S13]); walking charge V = R·n·Δq and decay through about
2 × 10^10 Ω to ground, so a body's charge fades over about 3 s (Jonassen [S18]); body voltage
from walking on vinyl, 250 V at 65–90 % humidity to 12 kV at 10–20 % (Desco [S17]); Bengaluru
humidity 37–58 % in the afternoon, 85–89 % in the morning (GKVK normals [S23]); ADC noise 2 mV
(ADS1115) or 21.8 mV (ESP32) [S15]; the 50 Hz hum on the body changes with contact (Elfekey
[S22]).

Three alarm rules were compared:
- **A** the active sweep alone (today's design);
- **B** active sweep, or any passive contact step (earthed metal rejected indoors by the hum);
- **C** active sweep, or a passive contact step confirmed by motion within 3 s.

## What it shows

1. **The physics works with very small charges.** With the improved input and an ADS1115, a
   difference of about **0.4 V between the two people** is enough to catch 90 % of shoulder
   grabs; with today's input and the ESP32 ADC it takes about **25 V**. Measured walking voltages
   on vinyl are 250 V and up, so the margin can be large.
2. **Coverage jumps from the wrist to the whole body.** Averaged over seven body locations, rule A
   catches 13 % of grabs (wrist only). Rule B catches about 94–96 %, rule C about 70 % (fig 15,
   16). Clothing barely matters: fabric is a large capacitor compared with the body.
3. **But rule B triples the unwanted prompts:** about 18 per hour instead of 5.5, because every
   harmless brush on a bus and every grab of a metal pole also makes a step.
4. **Rule C keeps prompts near today's level** (about 7.8 per hour) and still covers about 70 %
   of the body. Its coverage is set almost entirely by how often motion confirms a real grab
   (54 % / 71 % / 87 % coverage if motion confirms 50 / 70 / 90 % of grabs).
5. Humidity hardly changes the answer **if** the vinyl table applies, because even humid-day
   voltages are far above what the improved input needs.

## What is still unknown (and why the 70–95 % is not a device claim)

- **The voltage between two strangers on Indian roads, tiles and bus floors.** The only published
  values found are for vinyl and carpet with insulating shoes, which favour static. Conductive
  floors and wet weather could pull voltages towards zero; fig 15 shows coverage against this
  unknown so the answer can be read off once it is measured.
- **Her own movement while charged.** When her body sits at hundreds of volts, moving her arm or
  sitting down changes her capacitance and her voltage by several volts, much bigger than a
  touch step. The model only removes footstep steps (by the accelerometer) and slow approaches
  (by rise time: a touch is under 10 ms, an approach takes over 0.3 s). Separating a touch from
  her own quick movements by rise time needs real recordings; until then this is the main risk
  of false steps.
- **Motion confirmation rates.** No paper gives how often a wrist accelerometer registers
  agitation after a real grab, or after a harmless brush. The 50–90 % and 5–20 % used here are
  estimates. Published wrist results are encouraging but not this task: gunshot recoil detected
  with 99.4 % accuracy in the lab (Loeffler [S27]); stated false-alarm budget for wrist fall
  detectors about 1 per day (US 10,950,112 [S31]).
- **Event rates** (brushes, railings per hour) are the same estimates `event_stream.py` uses.

## What would cut false alarms further

- **Rise time:** a touch moves her voltage in under a millisecond; approaches, her footsteps and
  most of her own movements take tens to hundreds of milliseconds. Sampling the passive channel
  at 1 kHz or more and keeping only sharp steps is the single most useful filter.
- **The 50 Hz hum, indoors:** touching earthed metal removes most of the hum on her body; another
  person changes it but does not remove it (Elfekey [S22]).
- **Contact that lasts:** while his hand stays on her, their bodies stay coupled. Her voltage then
  responds to her own movement about half as much, and the hum changes; a "still touching" check
  for 1–2 s after the step would stand in for the 2 s hold the active sweep uses.
- **Physiology as a slow confirmation:** wrist stress detection reaches 87 % balanced accuracy
  (Siirtola [S28]); too slow to trigger, but useful to raise confidence in an alert.
- **Audio:** distress-scream detection with a context filter drops false alarms from about 10 % to
  about 1 % of the time (arXiv 2608.04176 [S30]); still too many alone, useful as a confirmation.

## Time-domain simulation and the fused watch (14 October 2026)

The step suggested above is now built. `sg_passive.py` simulates her body voltage at 500 Hz and a
wrist accelerometer at 50 Hz: walking charge and leak (V = R n dq, tau about 3 s [S18]), charge
shared at contact (bare skin or fabric [S7, S13]), a charged person walking up (C_AB [S12]),
earthed metal holding her at 0 V (and removing the 50 Hz hum indoors [S22]), a phone or bag
(4–12 pF) pulling her a few % toward 0 V, and her own arm movement changing her capacitance by
about 3 %. `passive_stream.py` runs grabs at 7 body places and hours of walking, bus and desk life
through the firmware detectors (fig 17, 18; `data/passive_stream_results.json`).

**Firmware contact-step detector** (tested, not assumed). A step must:
1. exceed 6x the noise in one 2 ms sample;
2. settle at once (move under 30 % of the step over the next 30 ms) and not be moving before it;
3. stand out from the signal around it: the 3-sample jump must exceed 8x the local roughness
   (median absolute deviation over ±50 ms). This removed the last false steps from her own
   footsteps and arm movements, and made heel-strike gating unnecessary.

It then classes the step: **earthed metal** (pulled to and held at 0 V, or the hum gone indoors),
**small object** (pulls her less than 12 % toward 0 V), or **another person**. In 90 simulated
minutes of walking, bus and desk life at body voltages of 1, 100 and 1,000 V it found no false
steps; it caught 93–97 % of contacts with the improved input at 1–10 V.

**Fused rule F** (now the default in the digital twin):
- *wrist path:* the active sweep held 2 s AND a person step within 4 s before the hold began;
- *anywhere path:* a person step AND agitation (2 or more jerks over 1.25 g within 3 s).

Her own hand on the watch, a metal pole, a phone and a table make no person step, so they never
prompt; a brush on a bus makes a person step but no pulling.

**Results** (improved input + ADS1115; 40 grabs per place and voltage, 6 h per place):

| Body voltage | Rule A (today) body coverage | Rule F body coverage | Unwanted prompts/h, A | Unwanted prompts/h, F |
|---|---|---|---|---|
| 1 V | 13 % | 71 % | 4.3 | 0.00 |
| 10 V | 13 % | 67 % | 4.8 | 0.00 |
| 100 V | 13 % | 70 % | 5.0 | 0.06 |

Unwanted prompts exclude a friend holding her wrist (a real touch by another person: the PIN is
the right answer there, about 0.3 per hour at a desk). Rule F catches 90–93 % of wrist grabs
(rule A also 90–93 %) and 58–73 % at every other place. Across all voltages F averaged 0.05 unwanted
prompts per hour, about one every 20 hours, against about 5 per hour today.

With today's input and the ESP32 ADC the fused rule needs body voltages of 10 V or more; below
3 V it would miss even wrist grabs. **The bootstrapped input with an ADS1115 is required.** A
fallback (F+: active hold for 6 s with no earthed step) keeps wrist grabs at low voltages but
brings back about 2.5 prompts per hour, so it is not recommended.

**What limits coverage:** a grab that only holds, without pulling, is missed away from the wrist
(30 % of grabs here, an estimate). **What the numbers rest on:** body voltages on Indian floors,
how often a grab pulls her arm, her reaction, and real arm-movement statistics are all estimates
until measured; the digital-twin check (`node demo/check_demo.js`) reproduces the Python rates
with the same physics in JavaScript.
