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
| SIM800L GSM | 2G only; Jio has no 2G and Airtel/Vi are winding it down | 4G module with VoLTE (a voice call to 112 needs VoLTE; LTE Cat-1 data/SMS alone cannot call) plus GNSS; the A7670 series is fine for the Gate 1 bench |
| ESP32 | Fine for Gate 1 | Flagship: two processors (see below) |

### Flagship architecture (ANVAYA 2k26 design; replaces the single-ESP32 plan above)

This is the architecture every other file now follows; the ESP32 is kept only as the Gate 1
bench controller and as the "current front end" baseline in the physics study.

| Block | Part | Role |
|---|---|---|
| Safety core | nRF5340 (Zephyr, "SparshaOS") | Runs Guard Mode alone (`demo/firmware.js` is its logic): sensing, PIN, duress, strap removal, alerts |
| App processor | STM32U5G9 | 1.43″ AMOLED UI, apps; only draws the PIN screen and forwards keys, so a frozen app cannot block an alert |
| Active sweep | AD9833 + LC tank + detector | Touché sweep through the strap electrode |
| Static channel | Bootstrapped input (LMP7721) + ADS1115 | Body-voltage steps on the same electrode |
| Motion | BMI270 | Pull, struggle, running |
| Body signals | MAX86141 (PPG), MAX30003 (ECG), MAX30208 (temperature), EDA | Heart rate, skin response |
| Cellular | 4G VoLTE + GNSS module, own nano-SIM | SMS, live location, 112 call |
| Wireless | nRF7002 (Wi-Fi 6), Bluetooth 5.3 (nRF5340), NFC | Phone app, updates |
| Power | nPM1300, 500 mAh, wireless charging | |
| Security | SE050 secure element | PINs and keys |

Open hardware questions (6 Nov 2026 audit): no power budget exists yet for a continuous sweep plus
LTE standby; no wearable impedance chip covers the full 1 kHz–3.48 MHz sweep (MAX30009 reaches
806 kHz, AD5940 200 kHz), so re-run the study on a truncated sweep before choosing the front end.

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
longer hold; capacitive plus accelerometer pull: 1–2 s; strap removal: immediate, implemented,
and checked from the moment Guard Mode is on); monitor
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
- Use the readings to calibrate `simulation/sg_model.py` (see README), then regenerate the dataset.

## Next steps

- Gate 1 build and calibration of the simulator.
- Add accelerometer simulation and motion fusion to cut nuisance prompts (currently about 5.5 per
  hour at a 0.3%-of-full-scale threshold, mostly the strap on metal, her hand on the watch and the
  wrist on a table).
- Consider an external ADC (e.g. ADS1115): it lowers the noise floor. Note that with the 3D field
  result a forearm grab 1–5 cm from the strap changes the sweep by only ~0.01–0.04% (typical
  values), so a quieter ADC alone won't make forearm grabs visible.
- Consider a titanium back plate: ~2.3x better skin contact than stainless steel (Goyal 2022).
- Optional: FEM study of electrode geometry. (The PIN / duress state machine now has its own
  tests: `node demo/test_firmware.js`.)

## Guard Mode rules (6 Nov 2026)

Added in the consistency pass so the logic matches the flagship's "the safety core cannot be
blocked" promise; all are in `demo/firmware.js` and tested in `demo/test_firmware.js`:

- Switching Guard Mode off needs her PIN. A wrong PIN on the off screen starts the 15 s PIN
  prompt; the duress PIN shows "Guard Mode off" but alerts silently and keeps guarding.
- It cannot be switched off while a PIN prompt is running.
- After a duress PIN the watch does not prompt again (that would show the attacker a second
  prompt); further touches are added to the silent alert.
- An alert ends only with her real PIN ("I'm safe"), and her contacts are told.
- Strap removal is checked during the 5 s of learning too.
- PINs are hers (`setPins`): two different 4-digit codes; 1234 / 9999 are only the demo defaults.
