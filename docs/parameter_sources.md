# Where every model value comes from (simulation v0.3)

v0.1 used engineering guesses for everything. v0.2 replaced them with published measurements
wherever one existed. v0.3 adds six more sources (S10–S15) for skin under a metal electrode, the
watch's return path, body-to-body coupling, hand area, shield performance and ADC noise. Geometry
calculations cover values that follow from the watch's size, and a short, clearly marked list of
estimates remains for Gate 1 to measure. Every value is also in
`SparshaGuard_paper_values.xlsx` with its full reference.

Tags used here and in `sg_model.py`:

- **[S#]** taken from a published source (list at the bottom)
- **[G]** computed from geometry (parallel-plate or self-capacitance formula)
- **[D]** a design choice for our watch
- **[E]** still an estimate; no published value found, so Gate 1 should measure it

## What the proposal's own references provide

The proposal cites 11 references. Only two are technical:

- [5] **Touché** (Sato, Poupyrev, Harrison, CHI 2012)
- [6] **Capacitive Fingerprinting** (Harrison, Sato, Poupyrev, UIST 2012)

The other nine cover crime statistics (NCRB), the panic-button rules, and news coverage of
competing products. They contain no electrical values.

From [5] and [6] we now use:

| Value | From the paper | Used in the model |
|---|---|---|
| Sweep range and steps | 1 kHz to 3.5 MHz, 17.5 kHz steps, 200 per sweep | Exactly this grid |
| Excitation | 6.6 V peak-to-peak sine, current well under 0.5 mA | Results are in % of full scale, so the drive amplitude cancels out |
| What is measured | Amplitude only (envelope detector); phase not measured | Score and classifier use amplitude only. Phase is kept in a separate file for a future lock-in design |
| Sweep time | ~33 ms per sweep (about 30 sweeps per second) | Event stream: 5 frames per second; the noise level assumes a sliding average of ~16 sweeps (~0.5 s) |
| ADC | 12-bit | Basis for the noise estimate |
| Trunk resistance | ~100 Ω | Added to the limb resistance |
| Dry intact skin | ~1 MΩ | Sets the dry end of the skin-hydration range |
| Classifier | SVM on the raw sweep | SVM (plus random forest for comparison) |
| Drift | Fingerprints drift over a day (temperature, hydration); re-login needed | Slow sweat drift and an adaptive baseline in the pipeline |
| Best single frequency | 753.5 kHz gave 87.3% vs 97.3% for the full sweep [6] | Supports using the whole sweep |

### Accuracy benchmarks from Touché worth quoting

These are real measured results, useful for setting expectations in the proposal:

- On-body sensing, electrodes on both wrists, 5 gestures: **84.0%** per user, **52.9%**
  walk-up (no per-user training). With 3 gestures, walk-up rose to 87.1%.
- The hand-held mobile mockup, which couldn't be grounded, was described as the hardest setup.
- Grounded setups (doorknob, table) reached 93–99%.

So the 99% in the proposal is a grounded, lab, per-user figure. A floating wrist device should
expect lower accuracy, which is what this simulation also shows.

## Circuit

| Parameter | Value | Tag | Source / reasoning |
|---|---|---|---|
| Series resistor Rs | 10 kΩ | [S3] | Open-source Arduino Touché circuit (Honigman et al., NIME 2014, Fig. 2) |
| Inductor L | 10 mH ±5% | [S3] | Same circuit. Touché itself used ~100 mH [S1]; the 10 mH Arduino version is what you'll build |
| Tank capacitor | 100 pF ±5% | [S3] | Same circuit |
| Sense-node parasitics | 2–7 pF | [S8]/[E] | Buffer input 2.1 pF [S8]; op-amp inputs ~5 pF; plus traces |
| Measurement noise | 0.1% of full scale per point | [S15]/[E] | ESP32 built-in ADC fluctuates ~21.8 mV (~0.66% of 3.3 V) [S15]; after 16 averaged sweeps that is 0.03–0.17% depending on whether the figure is p-p or std. dev. An external ADC (ADS1115, ~2 mV [S15]) would be ~5–10x quieter |

## Wearer's body

| Parameter | Value | Tag | Source / reasoning |
|---|---|---|---|
| Body to surroundings, street shoes | 110–170 pF | [S4] | Jonassen AC-bridge measurements: shoes on asphalt 110–115 pF, on linoleum 160–170 pF |
| Barefoot on a hard floor | 185–250 pF | [S4] | Barefoot on asphalt 185 pF, on linoleum 250 pF |
| Sandals | 130–210 pF | [E] | No measurement found; placed between shoes and barefoot |
| Seated in a car | 150–300 pF | [E] | No measurement found; thick seat foam to the metal body |
| Cross-check | ~150 pF | [S5] | Maity et al. measured ~150 pF body-to-ground |
| Walking changes | ±5% C_BE while walking | [S4]/[S9]/[E] | Feet are the main source of body-capacitance variation [S4, S9]; the size is an estimate |
| Wrist-to-trunk tissue | 100–400 Ω + 100 Ω | [S5]+[S1] | Limb/subcutaneous tissue 100–400 Ω [S5]; trunk ~100 Ω [S1] |
| Second person | Same footwear data | [S4] | |

## Skin and contact

| Parameter | Value | Tag | Source / reasoning |
|---|---|---|---|
| Stratum corneum resistance | 6.4 MΩ·cm² (dry) → 3.0 MΩ·cm² (hydrated) | [S10] | Goyal et al. 2022, fitted for dry metal electrodes |
| Stratum corneum capacitance (CPE) | 41 nF/cm² (dry) → 190 nF/cm² (hydrated), exponent 0.88–0.92 | [S10] | Same paper; exponent ≈ 0.9 |
| Metal-to-skin contact (CPE) | 114 nF/cm² stainless steel (dry), ×1.57 when hydrated; exponent 0.5–0.6 | [S10] | Hydrated factor from the paper's titanium values (267 → 420) |
| Hydration | 0 (dry) to 1 (hydrated), interpolated on a log scale | [S10] | Replaces v0.2's estimated 0.1–3 factor |
| Cross-check | Palm stratum corneum G_DC 4.4 µS/cm², C0 50 nF/cm², m 0.8 | [S6] | Martinsen et al. 1997; same order of magnitude |
| Inner electrode | 2–4 cm² stainless steel | [D] | Titanium would give ~2.3x more contact capacitance [S10] |
| Hand contact area (grab) | 40–80 cm² | [S13] | 30–55% of an adult hand's palmar area (132–147 cm², Indian adults) |
| Clothing permittivity | εr 1.2–5.1 | [S7] | Ng & Reaz 2017: polyester 1.18, nylon 1.22, cotton 3.0, linen 4.0, rayon 5.1 (1 kHz) |
| Clothing thickness | 0.16–0.58 mm per layer, 1–2 layers | [S7]/[E] | Same paper; the layer count is an estimate |
| Outer-electrode coating | 25–100 µm, εr 3 | [D] | Thin polymer coat; our choice |

**Finding:** with these published skin and fabric values, skin and clothing have only tens to
hundreds of ohms of impedance at the sweep frequencies (the dry steel electrode about 1.5 kΩ at
100 kHz). That is small compared with the picofarad paths to the surroundings. Clothing barely
hides a touch; what decides detectability is how the floating watch connects back to earth.

## The watch's own couplings

| Parameter | Value | Tag | Source / reasoning |
|---|---|---|---|
| Watch ground to wrist (PCB) | ~3–13 pF | [G] | Ground plane 8–12 cm², 2–4 mm through the case back, εr 1.5–2.5 |
| Outer strap electrode to wrist (no shield) | ~15–60 pF extra | [G] | 20–30 cm² of electrode through a 1.5–3 mm strap of εr 2.5–3.5 |
| Driven-shield residual | 20–50% | [S14] | TI measured 23–66% of unwanted coupling remaining for flat shields; ~23% for a ring + underside shield larger than the electrode |
| Watch return path, single electrode | 0.4–1.5 pF | [S11]/[S5]/[G] | Free-space self-capacitance 8ε₀a ≈ 1.2 pF for a 3.5 cm board, times the wrist factor x = 0.364 [S11] ≈ 0.45 pF; Maity et al. measured ~1.5 pF [S5] |
| Watch return path, with outer electrode | 0.6–2.0 pF | [G]/[S11]/[E] | A ~5–6 cm conductor ring round the wrist: 8ε₀a × 0.364 ≈ 0.65–0.75 pF; upper end estimated |
| Car nearby | ×1.3–2 on return path | [E] | |
| Lab-bench earthing | 10 nF | [E] | Represents USB to a mains-earthed laptop |

**Findings:** the outer strap electrode without a shield adds tens of pF of coupling to the
wrist. A real driven shield removes only half to three-quarters of it [S14], so the shield helps
but does not make the problem disappear. The return path at the wrist is smaller than v0.2
assumed [S11], which makes touches away from the electrode even harder to see.

## Events

| Event | Model | Tag |
|---|---|---|
| Bare-skin grab | Two stratum corneum layers in series over 40–80 cm² | [S10]/[S13] |
| Grab through clothing | Skin + fabric capacitor + skin | [S10]/[S7] |
| His palm on the outer electrode | His skin over 10–20 cm² + coating | [S10]/[D]/[E] |
| His hand near the strap (forearm) | 3D solve, grip 1–5 cm from the strap: ~0.12–1.4 pF with the outer electrode, ~0.03–0.35 pF single (was 0.5–3 pF until 12 Oct 2026) | [G] 3D, FastCap-checked; grip position [E] |
| His body 0.3–0.6 m from the watch (shoulder etc.) | 2–20% of the watch's return path (~0.02–0.3 pF) | [E] |
| Bystander, no touch | 21–40 pF body-to-body | [S12]/[E] | 21 pF at 1 m by FEM (Nath et al. 2021); higher when closer, upper end estimated |
| Her own hand on the strap | Outer-electrode contact + both arms (2 × 100–400 Ω) | [S5]/[E] |
| Hand on an earthed railing | Skin + metal contact over 20–40 cm² to earth | [S10]/[E] |
| Strap pressed on a metal pole | Coating over 2–10 cm² | [G] |
| Holding a phone | Skin + phone self-capacitance 4–12 pF | [G]/[E] |
| Wrist on a wooden table; bag | Small added couplings | [E] |
| Strap pulled off (digital-twin demo) | Electrode and ground plane 1–5 cm off the skin, in air: 0.05–0.3 pF and 0.05–0.5 pF | [G] |
| Sweat and strap movement | Hydration drift (minutes); strap-gap jitter 1.5–5% on the wrist coupling | [E] |


## Sensitivity check of the remaining estimates (11 October 2026)

Each estimate was swung across its full range to see whether it changes any result
(noise floor 0.11%, trigger 0.3% of full scale).

| Estimate | Range tested | Result | Status |
|---|---|---|---|
| His hand a few cm from the strap | 0.5 → 3 pF | Forearm grab 0.07% → 0.42% | **Matters.** Replaced by the 3D calculation on 12 Oct 2026 (below) |
| Wrist on a table | +1/+5 → +5/+20 pF | 0.14% → 0.66% | **Matters.** Measure on real tables in Gate 1 |
| Strap-gap jitter | 1.5% → 5% | 0.03% → 0.09% (drift) | Matters a little. Measure in Gate 1 |
| His palm on the strap | 10 cm²/100 µm → 20 cm²/25 µm | 13% → 19% | **Settled**: always far above the trigger |
| His body to watch (shoulder grab) | 2% → 20% of return path | 0.004% → 0.03% | **Settled**: always far below the noise |
| Car body factor | ×1.3 → ×2 | No change in any outcome | **Settled** |
| Body capacitance, sandals / car seat | 130–210 / 150–300 pF | Forearm grab unchanged (0.25%) | **Settled** |
| Holding a bag | +2 → +10 pF | ~0% | **Settled** |
| Railing grip area | 20 → 40 cm² | ~0% | **Settled** |

"Settled" means the true value can't change any conclusion, so the estimate stays as it is.

## 3D field calculation: his hand near the strap (integrated 12 October 2026)

Boundary-element electrostatic solve (`fem/hand_near_strap.py`; validated to 0.5% on a sphere
and 1.2% on a disc). Extra coupling with the outer electrode: 1.42 pF at 1 cm, 0.44 pF at 2 cm,
0.24 pF at 3 cm, 0.12 pF at 5 cm, 0.05 pF at 10 cm (single electrode about 4x lower). Confirmed
with FastCap to within 1% (`fem/fastcap_crosscheck.py`, fig 14). Since 12 October 2026 the model
uses this curve for a forearm grab (`hand_near_strap_pF` in `sg_model.py`), with his grip 1–5 cm
from the strap edge [E]; a grip closer than 1 cm counts as a wrist grab. This replaced the old
0.5–3 pF estimate and brought the forearm-grab median from ~0.26% to ~0.12% of full scale, at
the noise floor. See `whole_body_detection.md`.

## Values found for the remaining estimates (14 October 2026)

A literature search on 14 October 2026 looked for every value still marked [E] in `sg_model.py`,
`event_stream.py`, `sg_passive.py` and the demo. Page access was limited to abstracts and search
snippets; values seen only second-hand (press releases, review tables) are marked "secondary" in the
workbook. All 34 new values and 27 new sources (S32–S58) are in `docs/SparshaGuard_paper_values.xlsx`.

**Now in the model**

| Was | Now | Source | Effect |
|---|---|---|---|
| Sense-node parasitics 2–7 pF [E] | buffer input 2.1–9 pF + traces 0.6–0.8 pF/cm × 1–3 cm | [S8], OPA350 datasheet [S35], trace capacitance [S36] | Wrist-grab signal 16.4 % → 16.0 % |
| Strap coating εr 3 [D] | parylene εr 2.65–3.15 | [S37] | Negligible |
| Walking change of body capacitance ±5 % [E] | 160 pF on both feet → 100 pF on one foot | Ficker [S40] (secondary) | Sweep: ≤ 0.002 % of full scale (settled). Static channel: her voltage rises 1.6× at every step; detector still finds no false steps |
| Gait timing (none) | double support 0–10 % and 50–60 % of the stride | Perry & Burnfield [S46] | When her capacitance changes in each step |
| Body leak resistance 2 × 10¹⁰ Ω | 2 × 10¹⁰ – 1 × 10¹¹ Ω (τ 3–25 s) | [S18], [S40]; 1–30 min to 100 V without ESD shoes [S32] | Slower decay of her charge |
| Cadence 1.7 steps/s [E] | 1.6–2.3 steps/s (women, 96–138 steps/min) | Tudor-Locke [S41] | |
| Her own movement changes C_B ~3 % [E] | 2–7 % (posture changes body capacitance by < 10 pF of ~150) | Neacsu [S42] | |
| Wrist walking motion 0.35 g at the step rate [E] | arm swing at half the step rate, amplitude π × ENMO, ENMO 140–350 mg | Dawkins [S43], [S44] | |
| Bus jolts 0.3–1.5 g [E] | 0.1–0.34 g (bus maxima 3.37 m/s² starting, 3.12 m/s² braking) | [S45], [S47] | Bus motion no longer looks like pulling |
| Her hand on the watch 3–6/h, 1–5 s [E] | 3/h, log-normal, median 5 s, mean 9 s | Visuri [S38] (140 sessions/day partly secondary) | Sweep-only design: more long touches |
| Phone 6–10/h, 30–200 s [E] | 5.3/h, log-normal, median 30 s, mean 212 s | Andrews [S39] (secondary) | |
| Contact settling "under 1 ms" | body model 150 pF / 330 Ω, τ ≈ 50 ns | IEC 61000-4-2 [S54] | Confirms a touch is a one-sample step |

**Found, used only as context or benchmark:** body voltage up to ±20 kV at 5 % RH and half the
voltage on concrete [S32]; face touching 23 per hour [S48]; train-interior touches [S49]; Bengaluru
metro crowd loads 4–8 per m² [S50] and commutes of ~42 min each way [S51]; wearable ground ≤ 1 pF to
earth [S53]; indoor 50 Hz field 9.6 V/m [S55]; fall-detector false alarms 0.025–0.3 per hour
[S33, S56]; aggressive-movement classification 99.6 % on scripted movements [S34]; sari insulation
[S57]; harassment in Hyderabad buses [S58].

**Still estimated (no published value found):** walking body voltage on Indian roads, tiles and bus
floors; how often a grab pulls her arm (70 %) and the size of those jerks (1.5–3 g); wrist peaks
from her own brisk gestures and their rate; how often strangers brush against her on a bus; how
long she holds a pole or rests her wrist on a table; capacitance of his hand closer than 1 m; a
phone's capacitance to ground; clothing layers and which body parts are bare; how quickly sweat
changes the skin under the watch. These are what Gate 1 recordings should measure.

## What Gate 1 should measure

These are the estimates that matter most for the results, in order:

1. **Watch return path to surroundings** on your actual board. Literature gives 0.4–1.5 pF;
   every touch away from the electrode depends on it.
2. **His hand on the outer electrode**: change in reading for a firm grab vs a light touch.
3. **Shield residual** on your actual shield layout (literature: 20–50%).
4. **Noise floor** of your ESP32 + envelope detector after averaging (literature suggests ~0.1%
   of full scale; an external ADC would be quieter).
5. **Strap-gap drift** while walking and moving the arm.
6. **Nuisance events**: wrist on a table, strap on a metal pole, own hand on the strap.
7. **Body capacitance in sandals and on a car seat** (no published measurement found).

## Sources

- **S1** M. Sato, I. Poupyrev, C. Harrison. *Touché: Enhancing Touch Interaction on Humans,
  Screens, Liquids, and Everyday Objects.* CHI 2012.
  https://la.disneyresearch.com/wp-content/uploads/touchechi20121.pdf
- **S2** C. Harrison, M. Sato, I. Poupyrev. *Capacitive Fingerprinting: Exploring User
  Differentiation by Sensing Electrical Properties of the Human Body.* UIST 2012.
  https://la.disneyresearch.com/wp-content/uploads/capacitive-fingerprintingcameraready1.pdf
- **S3** N. Honigman et al. *Techniques in Swept Frequency Capacitive Sensing: An Open Source
  Approach.* NIME 2014. https://nime.org/proceedings/2014/nime2014_515.pdf
  (Component list also in https://github.com/sofian/touche)
- **S4** N. Jonassen. *Human Body Capacitance: Static or Dynamic Concept?* EOS/ESD Symposium
  1998, pp. 111–117. https://backend.orbit.dtu.dk/ws/files/4363898/Jonassen.pdf
- **S5** S. Maity, M. He, M. Nath, D. Das, B. Chatterjee, S. Sen. *Bio-Physical Modeling,
  Characterization and Optimization of Electro-Quasistatic Human Body Communication.*
  IEEE Trans. Biomedical Engineering, 2019. https://arxiv.org/pdf/1805.05200.pdf
- **S6** Ø. G. Martinsen, S. Grimnes, O. Sveen. *Dielectric properties of some keratinised
  tissues. Part 1: Stratum corneum and nail in situ.* Med. Biol. Eng. Comput. 35 (1997)
  172–176. https://mn.uio.no/fysikk/english/research/projects/bioimpedance/publications/papers/blemme.pdf
- **S7** C. L. Ng, M. B. I. Reaz. *Characterization of Textile-Insulated Capacitive Biosensors.*
  Sensors 17 (2017) 574. https://doi.org/10.3390/s17030574
- **S8** S. Avlani, M. Nath, S. Maity, S. Sen. *A 100 kHz–1 GHz Termination-dependent Human Body
  Communication Channel Measurement using Miniaturized Wearable Devices.* DATE 2020.
  https://par.nsf.gov/servlets/purl/10249175

- **S9** *Body-Area Capacitive or Electric Field Sensing for Human Activity Recognition and
  Human-Computer Interaction: A Comprehensive Survey.* arXiv:2401.06000 (2024).
  https://arxiv.org/abs/2401.06000

- **S10** K. Goyal, D. A. Borkholder, S. W. Day. *Dependence of Skin-Electrode Contact Impedance
  on Material and Skin Hydration.* Sensors 22(21) (2022) 8510.
  https://www.mdpi.com/1424-8220/22/21/8510
- **S11** A. Datta, M. Nath, D. Yang, S. Sen. *Advanced Biophysical Model to Capture Channel
  Variability for EQS Capacitive HBC.* arXiv:2010.15339 (2020). https://arxiv.org/pdf/2010.15339
- **S12** M. Nath et al. *Inter-Body Coupling in Electro-Quasistatic Human Body Communication:
  Theory and Analysis of Security and Interference Properties.* Scientific Reports (2021).
  https://arxiv.org/pdf/2003.13329
- **S13** P. Agarwal, S. Sahu. *Determination of hand and palm area as a ratio of body surface
  area in Indian population.* Indian Journal of Plastic Surgery 43(1) (2010).
  https://www.thieme-connect.de/products/ejournals/pdf/10.1055/s-0039-1699403.pdf
- **S14** Texas Instruments. *Capacitive Sensing: Ins and Outs of Active Shielding.* SNOA926A
  (2015). https://www.ti.com/lit/pdf/SNOA926
- **S15** Hackaday.io. *ADC performance: Arduino vs ESP32 vs ADS1115.*
  https://hackaday.io/project/205380-adc-performance-arduino-vs-esp32-vs-ads1115
  (weak source; with Espressif's ADC notes, https://developer.espressif.com/blog/2025/08/adc-performance/)

Added 14 October 2026:

- **S32** A. Talebzadeh, M. Moradian, Y. Han, D. E. Swenson, D. Pommerenke. *Effect of Human Activities and Environmental Conditions on Electrostatic Charging.* IEEE Trans. Electromagnetic Compatibility 58(4), 2016. https://doi.org/10.1109/TEMC.2016.2575842 (Values from the abstract)
- **S33** M. Kangas, R. Korpelainen, I. Vikman, L. Nyberg, T. Jämsä. *Sensitivity and false alarm rate of a fall sensor in long-term fall detection in the elderly.* Gerontology 61(1):61-68, 2015. https://doi.org/10.1159/000362720 (Abstract)
- **S34** F. Tchuente, N. Baddour, E. D. Lemaire. *Classification of Aggressive Movements Using Smartwatches.* Sensors 20(21):6377, 2020. https://doi.org/10.3390/s20216377 (Abstract; scripted movements)
- **S35** Texas Instruments. *OPA350, OPA2350, OPA4350 high-speed single-supply rail-to-rail operational amplifiers (SBOS099D).* Datasheet, 2015. https://www.ti.com/lit/ds/symlink/opa350.pdf (Input capacitance, typical)
- **S36** ECN / passive-components.eu (using TI figures). *A Plague of Parasites (PCB trace capacitance).* Trade article, n.d. https://passive-components.eu/ (0.8 mm trace on 0.8 mm FR-4 over a plane)
- **S37** Specialty Coating Systems. *Parylene Dielectric Properties.* Manufacturer technical data, n.d. https://scscoatings.com/ (Parylene N and C relative permittivity)
- **S38** A. Visuri, Z. Sarsenbayeva, N. van Berkel, J. Goncalves, R. Rawassizadeh, V. Kostakos, D. Ferreira. *Quantifying Sources and Types of Smartwatch Usage Sessions.* Proc. ACM CHI 2017, pp. 3569-3581, 2017. https://doi.org/10.1145/3025453.3025817 ('Half of sessions under 5 s' in the abstract; 140 sessions/day and ~9 s mean via University of Oulu news)
- **S39** S. Andrews, D. A. Ellis, H. Shaw, L. Piwek. *Beyond Self-Report: Tools to Compare Estimated and Real-World Smartphone Use.* PLoS ONE 10(10):e0139004, 2015. https://doi.org/10.1371/journal.pone.0139004 (85 uses/day and ~5 h/day via Lancaster University press release)
- **S40** T. Ficker. *Charging by walking.* J. Phys. D: Appl. Phys. 38(5):410-417, 2005. https://incompliancemag.com/charging-by-walking/ (Numbers seen in In Compliance Magazine's summary of Ficker's work (secondary); check the paper)
- **S41** C. Tudor-Locke, H. Han, E. J. Aguiar, et al. *Using cadence to study free-living ambulatory activity.* Sports Medicine 42(5):381-398, 2012. https://strathprints.strath.ac.uk/42646/
- **S42** D. Neacsu, A. Salceanu, E. Lunca, V. David. *Indirect Measurements on the Capacity in the Electrostatic HB Model.* IMEKO TC4 Symposium, Iasi, 2007. https://imeko.org/proceedings/indirect-measurements-on-the-capacity-in-the-electrostatic-hb-model (Abstract/snippet)
- **S43** N. P. Dawkins, T. Yates, et al. *Normative wrist-worn accelerometer values for self-paced walking and running: a walk in the park.* J. Sports Sciences, 2022. https://doi.org/10.1080/02640414.2021.1976491 (Averaged ENMO values, not peaks)
- **S44** (authors as listed on arXiv). *A 'one-size-fits-most' walking recognition method for smartphones, smartwatches, and wearable accelerometers.* arXiv:2207.07443, 2022. https://arxiv.org/abs/2207.07443
- **S45** (authors not visible in the abstract). *Perturbation in public transport as a basic concept for perturbation-based balance training for fall prevention.* Z. Gerontol. Geriatr., 2020. https://link.springer.com/journal/391 (12 days of bus and tram recordings, sensor on a vertical bar)
- **S46** J. Perry, J. M. Burnfield. *Gait Analysis: Normal and Pathological Function, 2nd ed..* SLACK Inc., 2010. https://www.healio.com/books (Standard gait-phase percentages)
- **S47** S. Krašna, et al. *Human Response to Longitudinal Perturbations of Standing Passengers on Public Transport During Regular Operation.* Frontiers in Bioengineering and Biotechnology 9:680883, 2021. https://doi.org/10.3389/fbioe.2021.680883
- **S48** Y. L. A. Kwok, J. Gralton, M.-L. McLaws. *Face touching: a frequent habit that has implications for hand hygiene.* American Journal of Infection Control 43(2):112-114, 2015. https://doi.org/10.1016/j.ajic.2014.10.015
- **S49** S. Mow, S. Seriani, T. Fujiyama. *Where and how often do people touch train interiors? An investigation during the pandemic.* Proc. ICE Municipal Engineer, 2024. https://discovery.ucl.ac.uk/id/eprint/10199779/
- **S50** Bangalore Metro Rail Corporation Ltd.. *Environmental Impact Assessment (design passenger loads).* BMRCL / JICA, n.d. https://www.jica.go.jp/
- **S51** Institute for Social and Economic Change. *Determinants of intra-urban mobility: a study of Bengaluru (Working Paper 437).* ISEC, 2019. https://ideas.repec.org/p/sch/wpaper/437.html
- **S52** Espressif Systems. *ESP-FAQ: ADC.* Espressif documentation, n.d. https://docs.espressif.com/projects/esp-faq/
- **S53** (Sen group, Purdue). *Step-to-Charge (EQS body powering).* arXiv:2408.01927, 2024. https://arxiv.org/abs/2408.01927
- **S54** IEC. *IEC 61000-4-2: Electrostatic discharge immunity test.* International standard, 2008. https://webstore.iec.ch/publication/4189 (Human-body model and current waveform)
- **S55** (Al-Quds / An-Najah University). *Residential exposure to ELF electric and magnetic fields in the city of Ramallah-Palestine.* Journal article, n.d. https://dspace.alquds.edu/items/bc4377ca-bfb7-4375-ab1a-435c8e020c57/full
- **S56** O. Aziz, et al. *Validation of accuracy of SVM-based fall detection system using real-world fall and non-fall datasets.* PLoS ONE 12(7):e0180318, 2017. https://doi.org/10.1371/journal.pone.0180318
- **S57** M. Indraganti, et al. *Thermal insulation of Indian clothing ensembles (sari, salwar-kurti).* Windsor Conference, 2014. https://architexturez.net/node/175314
- **S58** B. B. Majumdar, et al. (BITS Pilani Hyderabad). *Harassment of women in public transport, Hyderabad.* Transportation Research Record, n.d. https://journals.sagepub.com/home/trr (numbers via press coverage, secondary)
