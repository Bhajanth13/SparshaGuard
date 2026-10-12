# SparshaGuard design notes

Decisions and open questions from the design discussion on 11 October 2026, before and alongside
simulation v0.1, updated for v0.3 (sourced values). Read this with the proposal (2 October 2026),
`../README.md` and `parameter_sources.md`.

## Concept (from the proposal)

- Default-to-alert: once Guard Mode is on, another person's sustained touch (about 2 s) starts a
  15-second PIN countdown. Correct PIN cancels; no PIN or wrong PIN sends SMS with GPS to contacts,
  calls 112 and starts audio recording; a duress PIN shows "Cancelled" but alerts silently.
  Removing the strap in Guard Mode alerts at once.
- Sensing: swept-frequency capacitive sensing (Touché-style) through a skin electrode, sorted by
  a small on-device classifier into no contact / object / self / other person.

## Hardware changes to the proposal's parts list

| Proposal part | Issue | Suggested change |
|---|---|---|
| AD7746 capacitance-to-digital | Fixed excitation frequency and a few-pF range, so it can't do a frequency sweep or measure a ~100 pF body | AD9833 driving an LC tank into an envelope or lock-in detector read by the ESP32 ADC (DIY Touché). Alternatives: AD5933 (sweep up to ~100 kHz), FDC2214 (better single-frequency sensing). Later, for a watch-sized PCB: AD5940/AD5941 or MAX30009 |
| SIM800L GSM | 2G only; Jio has no 2G and Airtel/Vi are winding it down | 4G LTE Cat-1 module such as the A7670 series |
| ESP32 | Fine | ESP32-S3 if on-device audio keyword spotting is added |

## Sensing physics

- Shoes don't stop it. Capacitive coupling works through insulation; a person in shoes still
  couples about 110–170 pF to the surroundings (Jonassen 1998, measured). Simulation confirms footwear barely changes the
  wrist-grab signal.
- The real limit is the floating watch. On battery, the watch ground couples to the surroundings
  through only a few pF, so a touch far from the watch barely changes the reading.
- Fix: two electrodes. Inner electrode on the skin, outer electrode (coated mesh or conductive
  fabric over the case and strap) tied to the circuit reference. A hand gripping near the watch
  closes a short, strong loop through the outer electrode.
- Add a driven shield between the electrodes and the PCB to cancel the fixed parasitic
  capacitance. Without it, the strap electrode itself adds ~15–60 pF of coupling to the wrist
  and loads the sensor. A real flat shield removes only 50–75% of unwanted coupling (TI
  SNOA926); a ring shield larger than the electrode does best.

## Sensitivity without false triggers

Separate the two problems: make the signal big and clean, then decide what it means.

Signal: large outer electrode; good inner contact; driven shield; track the resonance-peak shift,
not only amplitude; lock-in detection; average 10–20 sweeps during the 2 s confirmation window;
filter 50 Hz mains hum; turn the radio off during each sweep.

Decision: trigger on fast step changes rather than a fixed level; freeze the adaptive baseline
during a suspected touch; hysteresis (enter higher than exit); tiered confidence (capacitive only:
longer hold; capacitive plus accelerometer pull: 1–2 s; strap removal: immediate); monitor
electrode contact separately; context modes (in vehicle, walking alone); thin insulating coat on
the outer electrode.

Measure false PIN prompts per hour of Guard Mode, not just accuracy. A friendly hug is real
"other person" contact; the PIN handles that, not the classifier.

## Touches away from the watch arm

The sensor can't reliably see a grab on the shoulder, waist, other arm or face (simulation: about
~0.11% of full scale, the same as the measurement noise). Cover these with:

1. Motion path: a TinyML model on accelerometer/gyroscope for struggle, pulling, being dragged,
   falls. Either path can start the PIN prompt.
2. On-device audio: scream or keyword spotting ("help", "bachao", "kaapadi"), only in Guard Mode,
   processed on the watch, nothing recorded until an alert fires.
3. Proximity mode for walking alone: someone within 10–20 cm for several seconds.
4. Future scope: a second linked wearable (pendant, anklet, clip).

Suggested proposal wording: "SparshaGuard directly senses contact at or near the wrist where it
is worn, and detects struggle, sudden pulling, falls and distress sounds regardless of where she
is grabbed."

Update (11 Oct): a passive body-potential channel on the same electrode could detect the
moment of contact anywhere on her body (charge sharing between two bodies at different
voltages). See `whole_body_detection.md`; it needs Gate 1 measurements before relying on it.

## Gate 1 test rules

- Run on battery and log over Bluetooth or Wi-Fi. USB to a charging laptop earths the circuit and
  makes a shoulder grab look ~20x bigger than on battery (v0.3).
- Test matrix: wrist, forearm, upper arm, other arm, shoulder, waist; bare skin and through
  clothing; shoes vs barefoot; tiled floor, road, car seat.
- Nuisance set: own hand on watch, strap on a metal pole, wrist on a table, phone, bag, bystander
  close, bus/metro, cooking, typing, rain, hugs, handshakes.
- Keep skin current tiny: AC-coupled electrode with a series resistor and capacitor; never wear
  it while the circuit is mains-powered.
- Use the readings to calibrate `sg_model.py` (see README), then regenerate the dataset.

## Next steps

- Gate 1 build and calibration of the simulator.
- Add accelerometer simulation and motion fusion to cut nuisance prompts (currently about 5.5 per
  hour at a 0.3%-of-full-scale threshold, mostly the strap on metal, her hand on the watch and the
  wrist on a table).
- Consider an external ADC (e.g. ADS1115): it lowers the noise floor. Note that with the 3D field
  result a forearm grab 1–5 cm from the strap changes the sweep by only ~0.01–0.04% (typical
  values), so a quieter ADC alone won't make forearm grabs visible.
- Consider a titanium back plate: ~2.3x better skin contact than stainless steel (Goyal 2022).
- Optional: Wokwi demo of the PIN / duress state machine; FEM study of electrode geometry.
