# Detecting a touch anywhere on her body

Question (11 October 2026): can SparshaGuard detect another person touching her on *any* part of
her body, not just near the watch? This note works through the physics, tests the options with
the simulation, and proposes a design. Figures: `figures/fig10`–`fig12`.

## 1. Why the current method only sees touches near the watch

The watch measures how her body loads its sense circuit. A touch far from the watch changes
only her body's capacitance to the surroundings (about 140 pF goes to about 280 pF). The watch
sees that change only through its own coupling back to the surroundings, which is about 1 pF.
Two tiny capacitors in series hide almost everything: the far touch shows up as about 0.02% of
full scale, a fifth of the noise.

**Can a better front end fix it?** Fig 10 tries the strongest changes available:

| Front end | Shoulder grab | Walking past a wall (no touch) | Bystander (no touch) |
|---|---|---|---|
| Current design | 0.02% | 0.02% | 0.01% |
| Tank 10 pF instead of 100 pF | 0.20% | 0.17% | 0.10% |
| + near-ideal shield (5% left) | 0.47% | 0.41% | 0.23% |
| + 3x bigger return path (best imaginable) | 1.11% | 0.91% | 0.54% |

A far touch can be made visible, but an ordinary change in the surroundings grows just as fast,
because both act through the same tiny return path. **No front-end change lets the active
sweep tell a shoulder grab from walking past a wall.** This is a limit of a small floating
device, not of our particular circuit.

## 2. His hand near the strap: 3D field calculation

A boundary-element electrostatic solve (`fem/hand_near_strap.py`, validated against an exact
sphere to 0.5% and a disc to 1.2%) gives the extra coupling when his hand grips her forearm a
given distance from the strap (fig 12):

| Gap to strap edge | With outer electrode | Single electrode |
|---|---|---|
| 1 cm | 1.42 pF | 0.35 pF |
| 2 cm | 0.44 pF | 0.11 pF |
| 3 cm | 0.24 pF | 0.06 pF |
| 5 cm | 0.12 pF | 0.03 pF |
| 10 cm | 0.05 pF | 0.01 pF |

Gaps under 1 cm didn't converge (the hand is nearly touching the strap; that case is the
"hand on the electrode" contact, modelled separately). The previous estimate was 0.5–3 pF; the
calculation says a forearm grab more than ~2 cm from the strap gives under 0.5 pF, which the
earlier sensitivity check showed is below the noise. **The active sweep reliably sees contact
only on or within about 1 cm of the strap.** (Integrated into the model on 12 October 2026.)

Checked with FastCap, MIT's reference capacitance solver (`fem/fastcap_crosscheck.py`, fig 14): the
two solvers agree to within 1% at every distance. With these values in the model, the share of
forearm grabs above the 0.3% threshold drops from ~40% to ~0%.

## 3. Ways to reach the whole body

| Approach | Covers whole body? | Reliability | Cost / burden | Verdict |
|---|---|---|---|---|
| Better active front end | Technically | Can't separate touch from surroundings (fig 10) | Low | Doesn't work alone |
| **Passive body-potential channel** (same electrode) | **Yes** | Depends on a voltage difference between the two people | Low: one extra amplifier | **Most promising** |
| Mains-hum (50 Hz) change | Yes, indoors | Needs nearby wiring; weak outdoors | Very low (same channel) | Useful extra cue |
| Motion (IMU) struggle detection | Indirect | Catches pulling, dragging, falls, not a still touch | Already planned | Keep |
| Audio (scream, keywords) | Indirect | Catches distress, not touch | Already planned | Keep |
| Electrodes in clothing | Yes, where the garment covers | Good | Wired garment; low acceptance | Future only |
| Second wearable (anklet, pendant) | Partly | Same limits per device | Extra device | Future only |

## 4. The passive body-potential channel

**Idea.** People carry static charge, so their bodies sit at different voltages. Walking alone
produces hundreds of volts or more: Desco lists 250–12,000 V for walking on vinyl, and
1,500–35,000 V on carpet. When another person touches her (anywhere: shoulder, hair, back, through
clothes), the two bodies share charge in a fraction of a millisecond. Her whole body's voltage
jumps by about half the difference between them.

**Why the wrist can see it.** This is a voltage step of her whole body, not a small capacitance
change. The floating watch sees a fixed fraction of it: C_GE / (C_GE + C_GB + C_input), about 6%
for the current design and about 30% with a bootstrapped input and a good shield. Fig 11:

| Voltage difference between the two people | Step at wrist, current design | Step at wrist, improved input |
|---|---|---|
| 0.1 V | 3 mV | 15 mV |
| 1 V | 30 mV | 153 mV |
| 10 V | 300 mV | 1.5 V |
| 100 V | 3 V | 15 V |

With a quiet ADC (ADS1115, ~2 mV), a difference of about 0.1–0.5 V is enough. The ESP32's
built-in ADC (~22 mV) needs about 1 V.

**Published support.** Bian et al. (PerCom 2019) built a wrist-worn passive electric-field
sensor sensitive to microvolt-level potential changes, which picked up motion of body parts
beyond the wrist and touch and proximity between people and objects. Their ProxiBand wristband
detected an approaching person with 74.3% true-positive rate indoors and 46% outdoors (Bian,
Liu, Lukowicz overview, 2025). Kurita (2016) detected the moment of contact from the induction
current caused by contact electrification. Elfekey et al. (Sensors 2016) used the 50 Hz hum
induced on the body for touch sensing.

**The hard parts, honestly:**
1. **Her own movement makes far bigger signals.** Every step charges her body (tens to hundreds
   of volts on insulating floors; Jonassen measured up to 3.5 kV on vinyl), so walking produces
   steps much larger than a touch. The accelerometer must be used to recognise her own steps,
   and a touch is a single sharp step that doesn't line up with a footstep.
2. **No difference, no signal.** If both people are at nearly the same voltage (humid monsoon
   air, conductive or wet footwear, both standing still), the step is small. How often this
   happens in Indian conditions is unknown; it must be measured.
3. **It detects contact with anything charged, not only people.** Touching a door handle or
   railing also causes a step. These can be told apart:
   - an earthed object (railing, tap) pins her body to 0 V and the 50 Hz hum mostly disappears;
   - another person shifts her voltage partway and changes the hum and step pattern, but
     doesn't remove them;
   - an insulating object (wooden table, plastic) causes little or no step.
4. **Safety.** The electrode can see volts to kilovolts during static events; the input needs
   standard ESD protection.

## 5. Proposed sensing design

1. **Active sweep (existing):** reliable contact at the wrist, and what touched it (person,
   own hand, object).
2. **Passive body-potential channel (new, same electrode):** a high-impedance, bootstrapped
   amplifier read by the external ADC. Detects the moment of contact anywhere on the body
   (charge-sharing step), and indoors a lasting change in 50 Hz hum while contact continues.
3. **Accelerometer:** removes her own step artefacts from the passive channel, and detects
   pulling, dragging and falls.
4. **Audio:** distress sounds, as planned.

A PIN prompt starts when a contact step is seen (anywhere) and it isn't explained by her own
footstep or an earthed object, or when the active sweep sees a hand at the wrist, or when
motion shows a struggle. The PIN still handles friendly contact.

## 6. What to test in Gate 1

- Passive channel: record the wrist signal while a second person touches the wearer on the
  shoulder, back, hair and arm, bare and through clothing; standing still and walking; tiled
  floor and outdoors; dry and humid days. The key unknown is how big the step usually is.
- Record her own walking, sitting down and standing up, to see how much the accelerometer
  removes.
- Record touching a railing, door handle, table and phone, to check the object signatures above.

## Sources (new in this note)

- Desco Industries, *Typical Electrostatic Voltages*. https://www.descoindustries.com/AboutESD/Voltage.aspx
- N. Jonassen, *Charging by Walking*, In Compliance Magazine (Mr. Static column). https://incompliancemag.com/charging-by-walking/
- S. Bian, V. F. Rey, J. Younas, P. Lukowicz, *Wrist-Worn Capacitive Sensor for Activity and
  Physical Collaboration Recognition*, IEEE PerCom 2019. https://dfki.de/web/forschung/projekte-publikationen/publikation/10312
- S. Bian, M. Liu, P. Lukowicz, *Passive Body-Area Electrostatic Field (Human Body Capacitance)
  for Ubiquitous Computing*, arXiv:2507.13520 (2025). https://arxiv.org/html/2507.13520v1
- K. Kurita, *Detection method for contact electrification based on electrostatic induction*,
  Electrostatics Joint Conference 2016. https://electrostatics.org/wp-content/uploads/2023/08/G12.pdf
- H. Elfekey, H. A. Bastawrous, S. Okamoto, *A Touch Sensing Technique Using the Effects of
  Extremely Low Frequency Fields on the Human Body*, Sensors 16(12):2049 (2016).
  https://doi.org/10.3390/s16122049
