# New sources for the remaining estimates (integrated into v0.3)

Found on 11 October 2026 while looking for published values to replace the [E] estimates in
simulation v0.2. **All of these were integrated into simulation v0.3 on 11 October 2026**, as
described under each "Suggested change". This file is kept as the record of what changed and why;
`parameter_sources.md` and `SparshaGuard_paper_values.xlsx` hold the current values.

## 1. Skin under a dry metal electrode — FOUND (the paper we couldn't read before)

**Goyal, Borkholder, Day. "Dependence of Skin-Electrode Contact Impedance on Material and Skin
Hydration." Sensors 22(21):8510, 2022.** https://www.mdpi.com/1424-8220/22/21/8510

- Electrodes: stainless steel 304 and titanium grade 2, dry, 4–9 cm². Same kind of electrode as a
  watch back plate.
- Measured 0.1 Hz – 100 kHz, in vivo (thigh, 10 people) and on a skin phantom.
- In vivo |Z| at 10 Hz: stainless steel 2.68 MΩ·cm², titanium 2.06 MΩ·cm².
- Fitted stratum corneum: dry Rsc 6.4 MΩ·cm², Csc 41 nF/cm²; hydrated Rsc 3.0 MΩ·cm²,
  Csc 190 nF/cm²; CPE exponent ≈ 0.9.
- Hydration effect: impedance about 10x lower; R about 2x lower, C about 4.6x higher.
- Titanium has 2.3x the contact capacitance of stainless steel, so lower impedance.

**Current model:** Martinsen's palm values (gel electrode) scaled by a dry↔sweaty factor of
0.1–3, which was an estimate.
**Suggested change:** use Goyal's dry and hydrated stainless-steel values directly for the inner
electrode; replace the estimated hydration factor with the measured dry↔hydrated range.
Expected effect on results: small, because skin is only tens to hundreds of ohms at our sweep
frequencies. It mainly makes the low-frequency end of the sweep (1–10 kHz) more realistic.
**Design note:** a titanium back plate would give lower, more stable contact than stainless steel.

## 2. Watch's return path to the surroundings, by body location — FOUND

**Datta, Nath, Yang, Sen. "Advanced Biophysical Model to Capture Channel Variability for EQS
Capacitive HBC." arXiv:2010.15339 (2020).** https://arxiv.org/pdf/2010.15339

- A device's return path is its free-space self-capacitance (8·ε₀·a for a disc of radius a)
  times a reduction factor x for being on the body.
- Measured x: **wrist 0.364**, elbow 0.214, shoulder 0.059, torso 0.146.
- Free-space return path for a few-cm device ≈ 1 pF.

**Current model:** 1.0–2.0 pF (single electrode), 1.5–3.0 pF (with outer electrode), based on
Maity et al.'s ~1.5 pF.
**Suggested change:** for a 3.5 cm watch board, 8·ε₀·a ≈ 1.24 pF × 0.364 ≈ **0.45 pF** at the
wrist, so a range of about 0.4–1.5 pF (Datta at the low end, Maity at the high end).
Expected effect: a smaller return path makes far-away touches even harder to see, and makes the
hand-on-outer-electrode path relatively more important. This is the single most important value
to measure in Gate 1.

## 3. Coupling between two people standing near each other — FOUND

**Nath et al. (Sen group, Purdue). "Inter-Body Coupling in Electro-Quasistatic Human Body
Communication: Theory and Analysis of Security and Interference Properties." Scientific Reports,
2021.** https://arxiv.org/pdf/2003.13329

- Body-to-body capacitance from electrostatic FEM: **21 pF at 1 m**, 6.6 pF at 5 m.
- Body-to-ground ~150 pF (agrees with our Jonassen and Maity values).

**Current model:** bystander 0.2–0.5 m away = 2–15 pF (my parallel-plate estimate).
**Suggested change:** at 0.2–0.5 m the coupling must be **above 21 pF**; use about 25–60 pF
(still needs the paper's Fig. 7a curve for exact values below 1 m).
Expected effect: crowded buses become a bigger nuisance source than the model shows now, though
still small for a floating watch.

## 4. Hand contact area — FOUND (Indian population)

**Agarwal, Sahu. "Determination of hand and palm area as a ratio of body surface area in Indian
population." Indian Journal of Plastic Surgery 43(1), 2010.**
https://www.thieme-connect.de/products/ejournals/pdf/10.1055/s-0039-1699403.pdf

- Whole hand (palmar side, fingers included): men 146.5 cm², women 132.4 cm².
- Palm only: men 77.9 cm², women 73.7 cm².

**Current model:** 40–80 cm² of contact for a grab.
**Suggested change:** keep 40–80 cm², now justified as roughly 30–55% of an adult hand
(a hand wrapped round a wrist can't touch with its whole surface). Cite this paper.

## 5. Driven-shield effectiveness — PARTLY FOUND

**Texas Instruments. "Capacitive Sensing: Ins and Outs of Active Shielding." SNOA926A, 2015.**
https://www.ti.com/lit/pdf/SNOA926

- With an active shield under and around the electrode, sensitivity to objects behind the sensor
  dropped by 51–76%, and to objects at the side by 34–77%, depending on shield size and ring.
- So 23–66% of the unwanted coupling remained.

**Current model:** shield leaves 2–10% of the watch-to-wrist coupling.
**Suggested change:** that looks optimistic. A range of about 10–50% residual is closer to
TI's measurements. A ring shield larger than the electrode does best.
Expected effect: the "inner + outer + driven shield" design would lose part of its advantage
over the unshielded version. Worth re-running to see how much.

## 6. ESP32 ADC noise — PARTLY FOUND (weak source)

**Hackaday.io project "ADC performance: Arduino vs ESP32 vs ADS1115."**
https://hackaday.io/project/205380-adc-performance-arduino-vs-esp32-vs-ads1115
**Espressif, "ADC performance" (2025).** https://developer.espressif.com/blog/2025/08/adc-performance/

- ESP32 built-in ADC fluctuation ~21.8 mV (about 27 LSB at 3.3 V); ADS1115 ~2 mV.
  The page doesn't say whether this is standard deviation or peak-to-peak.
- Espressif gives calibrated accuracy (±10 to ±30 mV depending on chip) and recommends a
  100 nF input capacitor and multisampling, but publishes no noise figure.

**Current model:** 0.05% of full scale after averaging 16 sweeps.
**Suggested change:** with the ESP32's built-in ADC, 16-sweep averaging gives roughly
0.05–0.17% of full scale, so the current value may be up to ~3x optimistic. An external ADC
(ADS1115 or similar) would beat the current value. Better: measure it on the Gate 1 board.

## Still not found

- Sandals and car-seat body capacitance (no measurement found).
- Strap-gap movement while walking (needs measurement).
- His hand a few cm from the strap (forearm grab): needs measurement or a 3D field model.
- Wrist on a wooden table, bag: no source; small effects.
