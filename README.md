# SparshaGuard

**A smartwatch for women's safety that raises the alarm when someone else grabs her.**
Team: Bhajanth V, Sukruth A Chinnur · RV University.

Most safety apps need her to find her phone and press SOS. SparshaGuard flips the default: once
Guard Mode is on, another person's hand held at the watch for 2 seconds starts a 15-second PIN
countdown. No PIN or a wrong PIN sends her live location to her contacts, calls 112 and records
audio. A duress PIN shows "Cancelled" but alerts silently. Pulling the watch off alerts at once.
The same electrode also reads her body's static charge, so a stranger who grabs her anywhere and
pulls her is caught too, while her own hand, metal, a phone or a brush in a crowd are ignored.

## Try the demo

**Online:** https://bhajanth13.github.io/SparshaGuard/ (front page), with the
[digital twin](https://bhajanth13.github.io/SparshaGuard/demo/) and the
[physics explorer](https://bhajanth13.github.io/SparshaGuard/explorer/).
The site is published by GitHub Pages from the `main` branch (Settings → Pages → Deploy from a
branch → `main`, folder `/ (root)`); `index.html` is the front page and `.nojekyll` makes GitHub
serve the files as they are.


Open **`demo/sparshaguard_demo.html`** in any browser (download it and double-click; it works
offline). Press **Play all** for the guided story (about 2 minutes), or switch to **Try it yourself**
and touch her. The watch's own decision logic runs on a simulated sensor built from the physics
below; nothing is scripted to succeed.

## Results at a glance

| | Result | How we know |
|---|---|---|
| Wrist grab, signal change | ~16 % of full scale (noise ~0.1 %) | circuit model; 60 published sources logged in total |
| Wrist grabs caught | 99 % (demo, fused watch), 83–93 % (studies) | 120 random trials; hours of simulated daily life |
| Grabs anywhere on her body | 61–70 % averaged over 7 places (first design: 13 %, wrist only) | `passive_stream.py`, demo check |
| Watch pulled off | 100 % caught, no false alarms | demo headless check |
| Unwanted PIN prompts | 0–1 in 9 simulated hours (demo); ~0.07 per hour (study). First design: ~3–4 per hour | same simulations |
| Model correctness | Python solver = SPICE to 0.0001 %; 3D solver = MIT FastCap within 1 % | `ltspice/`, `fem/` |

**How the fused watch decides.** A PIN prompt needs *another body*. When another person touches
her, the two bodies share static charge and her voltage jumps in under a millisecond; her own
footsteps and movements are slower, metal holds her at 0 V, and a phone pulls her only a few %.
So the watch prompts when (wrist) the sweep sees a hand held 2 s *and* another body touched her, or
(anywhere) another body touched her *and* the accelerometer feels her arm being pulled. Two
things are still estimates until Gate 1: how charged people are on Indian floors (results hold
from about 1 V to 100 V with the bootstrapped input and an ADS1115) and how often a grab pulls her
arm (70 % assumed; a grab that only holds is missed away from the wrist). See
`docs/whole_body_fusion.md`.

**Signs of assault from her own movement** (digital twin; thresholds are estimates, because no
published wrist data for assaults was found):
- *Struggling to get free* (accelerometer + gyroscope): 5 or more irregular jerks over 2 g in 4 s
  with the wrist turning faster than 400°/s asks for the PIN even when no touch was felt.
- *Running*: not an alarm by itself (people run for buses), but while she runs any touch asks for
  the PIN at once.
- *Microphone*: turns on when the PIN prompt starts; the correct PIN deletes the recording, and no
  PIN, a wrong PIN or the duress PIN sends it with SMS + GPS.
- *Heart rate*: confirmation only (it rises too slowly to start an alarm); the alert reports it.

**Honest status:** this is a simulation study. Every value comes from a published paper or from
geometry, and the remaining estimates are marked. The next stage, **Gate 1**, is a
battery-powered prototype whose measurements replace those estimates before any number is
quoted as a device result. A map of the whole project is in `docs/project_map.svg`.

## The science, in detail

Simulation study v0.3. It models what a battery-powered wrist sensor actually measures when
another person touches the wearer, generates a labelled synthetic dataset, trains contact
classifiers, and runs the full detection pipeline through simulated hours of daily life.

> **Status: sourced, not yet calibrated.** v0.3 takes its values from the proposal's Touché
> references and 14 further published sources (body capacitance with footwear, skin under a
> metal electrode, fabric, the watch's return path, body-to-body coupling, hand area, shield
> performance, ADC noise). Every value and its source is in `docs/parameter_sources.md` and
> `docs/SparshaGuard_paper_values.xlsx`. The values still estimated are marked [E]; Gate 1
> measurements on the real board should replace them before any number is quoted as a device result.

## How to run

```bash
pip install -r requirements.txt
python make_figures.py      # physics figures, fig0-fig4               (~40 s)
python make_dataset.py      # synthetic dataset, 18,000 events         (~15 s)
python train_classifier.py  # classifiers, fig5-fig7                   (~40 s)
python event_stream.py      # pipeline over simulated hours, fig8-fig9  (~30 min on 2 cores)
python event_stream.py --figs-only   # redraw fig8-fig9 from saved results
python build_explorer.py    # rebuild the interactive page after editing its sources
python rebuild_csv.py       # write the CSV from the .npz (numpy + pandas only)
python fem/hand_near_strap.py   # 3D field calculation: his hand near the strap (~2 min)
python whole_body.py        # whole-body touch study, fig10-fig12      (~5 s)
python ltspice/spice_crosscheck.py  # check the circuit solver against SPICE, fig13 (~5 s, needs ngspice)
FASTCAP=/path/to/fastcap python fem/fastcap_crosscheck.py  # check the 3D result against FastCap, fig14 (~2 min)
python fusion_study.py      # static channel on paper: rules vs body voltage, fig15-fig16 (~10 s)
python passive_stream.py    # time-domain static channel + fused alarm rules, fig17-fig18 (~2.5 min)
node demo/check_demo.js     # check the demo's sensor + firmware headless (~6 min)
python build_demo.py        # rebuild the digital-twin demo page (quotes demo/demo_check.json)
```

Open `explorer/sparshaguard_explorer.html` in any browser for the interactive explorer, and
`demo/sparshaguard_demo.html` for the digital-twin demo (both work offline except for web fonts).

## Files

| File | What it is |
|---|---|
| `sg_model.py` | The electrical model. Every parameter is tagged with its source |
| `docs/parameter_sources.md` | Every value, where it comes from, and what Gate 1 should measure |
| `docs/SparshaGuard_paper_values.xlsx` | Every value found in the papers, with full references |
| `docs/findings_integrated_v0_3.md` | What changed from v0.2 to v0.3 and why |
| `make_figures.py` | Equivalent circuit and physics figures |
| `make_dataset.py` | Monte Carlo dataset generator |
| `train_classifier.py`, `sg_features.py` | SVM and random-forest classifiers, evaluation |
| `event_stream.py` | Time-domain pipeline: baseline tracking, hysteresis, sustain rule, prompts per hour |
| `plotstyle.py` | Shared figure style |
| `ltspice/sparshaguard_wrist_grab.cir` | The same circuit as a netlist for LTspice / ngspice cross-checking |
| `ltspice/spice_crosscheck.py` | Writes a SPICE netlist for every design and scenario (`ltspice/netlists/`), runs ngspice and compares with the Python solver (fig13, `data/spice_crosscheck.json`) |
| `data/sparshaguard_synthetic_v0_3.csv` | The dataset, amplitude only; columns explained below. Not stored in the repo (40 MB): run `python rebuild_csv.py` |
| `data/sparshaguard_synthetic_v0_3.npz` | Same data as the CSV; `..._phase.npz` and `..._baseline.npz` add phase and baseline amplitude |
| `data/*.json` | Numeric results behind every figure |
| `models/svm_dual_shield.joblib` | Trained SVM for the recommended hardware design |
| `explorer/sparshaguard_explorer.html` | Interactive explorer page (built from `page_src.html` + `model.js`) |
| `demo/sparshaguard_demo.html` | Digital-twin demo: the watch firmware running on a simulated sensor (built by `build_demo.py` from `demo/page_src.html`, `demo/sensor.js`, `demo/firmware.js` and `explorer/model.js`) |
| `demo/check_demo.js`, `demo/demo_check.json` | Headless check of the demo's sensor and firmware against the study's rates |
| `build_explorer.py`, `rebuild_csv.py` | Rebuild the explorer page; rebuild the CSV from the `.npz` |
| `docs/design_notes.md` | Hardware changes, sensing physics, false-trigger strategy, Gate 1 test rules |
| `whole_body.py`, `docs/whole_body_detection.md` | Can it detect a touch anywhere on her body? Active-sweep limit, passive body-potential channel, proposed design (fig10–fig12) |
| `sg_passive.py` | Passive static channel in time: her body voltage at 500 Hz, wrist accelerometer, and the firmware's contact-step detector |
| `passive_stream.py`, `fusion_study.py`, `docs/whole_body_fusion.md` | Fused alarm rules (sweep + static + motion) over body places, places and body voltages (fig15–fig18) |
| `fem/bem_capacitance.py`, `fem/hand_near_strap.py` | Boundary-element electrostatic solver and the hand-near-strap 3D calculation |
| `fem/fastcap_crosscheck.py` | The same 3D calculation in FastCap, MIT's reference capacitance solver (fig14, `fem/fastcap_results.json`); build steps in its docstring |
| `figures/` | All figures, fig0–fig18, 200 dpi PNG |
| `docs/project_map.mmd`, `.svg` | One-page map of the whole project (Mermaid source and picture) |
| `docs/video_script_2min.md` | Narration and shot list for the 2-minute hackathon video |
| `video/` | Earlier 13-minute explainer (`SparshaGuard_Explained.mp4`, `.html`, narration script). **Outdated:** made before the 3D forearm result, so it overstates forearm grabs; see `video/README.md` |
| `archive/v0_1/`, `archive/v0_2/` | Earlier models, figures and results, for comparison |

### Dataset columns

`design` (single / dual / dual_shield), `environment` (street_shoes / sandals / barefoot_tile / car_seat),
`label` (no_contact / object / self / other_person), `subtype` (e.g. wrist, shoulder, bystander,
railing_wrist), `near_watch`, `score_pct` (RMS amplitude change, % of full scale), then
`da_000`–`da_199`: amplitude change at each of Touché's 200 sweep frequencies (1 kHz to 3.48 MHz
in 17.5 kHz steps), as a fraction of full scale. Frequencies are in `data/sweep_frequencies.csv`.

## The model in one paragraph

The open-source Arduino Touché circuit (10 kΩ, 10 mH, 100 pF tank) sweeps 200 frequencies from
1 kHz to 3.5 MHz, as Touché did, and an envelope detector reads the amplitude at the sense node.
The sense node touches the skin through a dry stainless-steel electrode (Goyal et al.). The watch
ground **floats** on the battery: it couples back to the surroundings through only about
0.4–1.5 pF (Datta et al., Maity et al.) and to the wrist through a few pF (geometry). The wearer
couples to the surroundings through 110–250 pF depending on footwear (Jonassen). A second person
couples to her through skin, fabric (Ng & Reaz) or just proximity (Nath et al.), and to the watch
through his hand on the outer electrode or through proximity. Three hardware designs are
compared: single electrode, inner + outer electrode, and inner + outer + driven shield (TI).

## Main findings (v0.3)

1. **Shoes and clothing are not the problem.** Footwear barely changes the wrist-grab signal
   (fig 3), and with measured skin and fabric values a hand through a shirt still couples strongly.
2. **Location is the problem.** With the recommended design, a wrist grab with his palm on the
   outer electrode changes the sweep by a median ~16% of full scale. Every other grab, the
   forearm included, changes it by ~0.11–0.12%, the same as the measurement noise (forearm uses
   the 3D field calculation since 12 Oct 2026; see "Checked against independent solvers"). The
   capacitive sensor alone can't see those grabs; they need the motion and audio paths (fig 2).
3. **The outer electrode is what makes wrist grabs visible.** Median wrist-grab change: single
   electrode ~0.25%, + outer electrode ~13%, + driven shield ~16%. A real driven shield only
   removes half to three-quarters of the strap's coupling to the wrist (TI), so its benefit is
   smaller than v0.2 assumed, but still positive.
4. **Bench tests mislead.** Earthing the circuit (USB to a charging laptop) makes a shoulder grab
   look about 20x bigger than on battery (fig 4). Gate 1 must run on battery.
5. **The sensor sees "a hand at the watch", but can't reliably tell whose.** His palm on the
   outer electrode and her own palm on it change the sweep almost identically (16.4% vs 16.2%
   with typical values). The classifier recognises her own hand as a hand 95–99% of the time and
   calls it "other person" only 3–6% of the time, but it calls a stranger's wrist grab "other
   person" only ~40% of the time and "a hand at the watch" 61–73% (fig 6). So the design should
   prompt for the PIN on any hand at the watch and let the PIN decide, not rely on the classifier
   to tell hers from his. The strap pressed on a metal pole is the main object that looks like a
   hand.
6. **Pipeline result (fig 9):** with a 0.3%-of-full-scale threshold and 2 s sustain, it caught
   ~88–93% of wrist grabs and none of the forearm or shoulder grabs, with ~4–5.5 unwanted PIN prompts
   per hour (1.5 walking, 7.5 commuting, 7.5 at a desk). The main causes are the strap pressed on
   a metal pole, her hand on the watch, the phone and the wrist on a table; 1.5 per hour at the
   desk were a friend holding her wrist, which is real contact. Adding the classifier as a gate
   cuts prompts to ~2 per hour but also drops wrist detection to ~49%, so it is not recommended.
7. **Accuracy is in line with Touché's own on-body result.** Random forest: 77% across four
   classes and 97% for "some hand is at the watch", measured on the events the sensor can see
   (wrist grabs, her hand, objects, no touch); grabs elsewhere are counted separately as missed. Touché measured 84% for on-body gestures with
   per-user training and 53% walk-up. The 99% in the proposal is for grounded lab setups.

## What changed between versions

| | v0.1 (guesses) | v0.2 (first sources) | v0.3 (all findings) |
|---|---|---|---|
| Circuit and sweep | 1 kΩ, 1 mH, 47 pF; 64 points | Arduino Touché; Touché's 200 points | same |
| Skin | Cole model, guessed | Palm stratum corneum (Martinsen) × guessed factor | Dry steel electrode, dry ↔ hydrated (Goyal) |
| Watch return path | 1.5–7 pF guessed | 1–3 pF (Maity) | 0.4–2 pF (Datta wrist factor + Maity) |
| Driven shield leaves | 10–30% guessed | 2–10% guessed | 20–50% (TI) |
| Bystander coupling | 0.3–3 pF guessed | 2–15 pF (geometry) | 21–40 pF (Nath FEM) |
| ADC noise | 0.05% relative | 0.05% of full scale | 0.1% of full scale (ESP32 measurement) |
| Hand contact area | 20–100 cm² guessed | 40–80 cm² guessed | 40–80 cm² (Agarwal & Sahu hand area) |
| Wrist grab, recommended design | ~16% | ~18% | ~16% |
| Far grabs (shoulder etc.) | ~0.4%, inside drift | ~0.06%, at noise floor | ~0.11%, at noise floor |
| Forearm grabs caught | ~89% | ~72% | ~43%, then 0% with the 3D coupling (12 Oct) |

The main conclusions held through all three versions. v0.3 is less optimistic about forearm
grabs and about the shield, mostly because of the noisier ADC and the weaker real-world shield;
the 3D field calculation then showed that forearm grabs are not visible at all.

## Checked against independent solvers

### Circuit: SPICE

`ltspice/spice_crosscheck.py` builds the same circuit element by element as a SPICE netlist and
solves it with ngspice, an industry-standard circuit simulator, on the same 200-point sweep.
SPICE has no constant-phase element, so each skin element is a fitted R-C ladder (Valsa et al.
2011), accurate to better than 0.004% over the sweep. Across 49 cases (3 designs × 14
scenarios, plus footwear and the USB-bench case) the two solvers agree to within 0.0001% of full
scale, about 1,000 times smaller than the ADC noise (fig 13). A deliberate 10% error in one
capacitor shows up as a 0.09% difference, so the check is sensitive enough to catch mistakes.
This confirms the solver and the wiring of the model; it does not check the parameter values,
which only Gate 1 measurements can do.

### 3D field: FastCap

`fem/fastcap_crosscheck.py` solves the hand-near-strap geometry again in FastCap (Nabors & White,
IEEE TCAD 1991), the multipole-accelerated capacitance solver from MIT used as a reference in
chip and package design. It has its own mesh and panel integrals. FastCap was first checked
against the exact capacitance of a sphere (0.16% error at 1,654 panels). On the finer mesh the
two solvers agree to within 1% at every distance (outer electrode: 1.42 vs 1.44 pF at 1 cm,
0.44 vs 0.44 pF at 2 cm, 0.049 vs 0.049 pF at 10 cm), and FastCap moves toward our result as its
mesh is refined (fig 14). Both solve the geometry in air; the strap plastic and the body's
tissue are not included in either.

### What the checks changed: forearm grabs are not visible

The 3D result (about 0.12–1.4 pF for a grip 1–5 cm from the strap) is well below the 0.5–3 pF
estimate the model used for a forearm grab. On 12 October 2026 the 3D curve replaced that
estimate in `sg_model.py` (`hand_near_strap_pF`), and the dataset, classifiers and daily-life
simulation were re-run. The forearm-grab median fell from ~0.26% to ~0.12% of full scale (the
noise floor), and forearm grabs caught fell from ~43% to 0%. The active sweep sees a grab only
when his hand is on or within about 1 cm of the strap. Wrist-grab results did not change.
Because forearm grabs are now invisible, the classifiers are trained only on grabs the sensor
can see (wrist), as the script already did for shoulder, waist and other far grabs.

## Digital-twin demo

`demo/sparshaguard_demo.html` runs the watch's decision logic on a simulated sensor, in real time,
for the hackathon demonstration. It is split the way the real device is:

- **Sensor twin** (`demo/sensor.js`): the circuit model (`explorer/model.js`, the JavaScript port
  of `sg_model.py`) plus sweat drift, strap jitter, foot movement and ADC noise, as in
  `event_stream.py`. It outputs only what an envelope detector gives: 200 amplitudes, 5 times a
  second. Each touch draws its details at random over the model's ranges (for example, his palm
  misses the outer electrode in 15% of wrist grabs).
- **Passive twin** (`PassiveTwin` in `demo/sensor.js`): the JavaScript port of `sg_passive.py`.
  Her body voltage at 500 Hz (walking charge and leak, charge sharing at contact, a person walking
  up, earthed metal, a phone, her arm movement, ADS1115 noise) and a wrist accelerometer at 50 Hz.
- **Firmware** (`demo/firmware.js`): the detection pipeline of `event_stream.py` (0.3% threshold,
  2 s hold, frozen baseline, no classifier gate), the static contact-step detector of
  `sg_passive.py` (sharp, settled, standing out from the signal around it; classed as another
  person, earthed metal or a small object), the fused rule F, a strap-removal check against the
  watch's own off-the-wrist signature, and the PIN state machine (15 s window, correct / wrong /
  duress PIN). It never sees which scenario is playing. "Show the science" can switch it back to
  the first design (sweep only) and change how charged people are.
- **Page**: one stage (where she is touched, her watch with a hold/countdown ring and the live
  sensor signal, the static channel with arm jerks, her contact's phone) and two modes: *Guided
  demo* (seven chapters with captions, "Play all" runs the whole story in about 2 minutes) and
  *Try it yourself* (nine touch tiles, including a shoulder grab that pulls, a brush in a crowd and
  holding her phone; answer the PIN on the watch). "Show the science" opens the
  sweep, the firmware log and the headline numbers.

`node demo/check_demo.js` runs the same files headless, with no scripted outcomes, and feeds
every sensor frame to two firmwares side by side (bodies at ~10 V; 70 % of grabs pull her arm):

| | First design (sweep only) | Fused watch |
|---|---|---|
| Wrist grabs caught | 92 % | 99 % |
| Grabs elsewhere (forearm, upper arm, other arm, shoulder, waist, face/hair) | 0 % | 65–66 % |
| Average over 7 places | 13 % | 70 % |
| Unwanted PIN prompts, 9 h of walking, bus and desk (incl. 2 runs per hour) | 28 (a metal pole, a table, her own hand) | 0 (earlier runs: 1, a brush while she moved her arm briskly) |
| Struggle to get free, no touch felt | 0 % | 99 % |
| Touch while she runs | 0 % | 99 % (running alone prompted 1.7 % of runs) |
| Strap removals caught | 100 % | 100 % |

No false strap alarms: normal wearing never comes closer than 2.0% to the off-wrist signature
(the alarm needs 0.4%). This matches `event_stream.py` and `passive_stream.py` within the
run-to-run spread. Strap removal is a new event in `sg_model.py`
(`strap_off`: electrode and ground plane 1–5 cm off the skin, in air).

## Calibrating with Gate 1

The list of what to measure, in priority order, is at the end of `docs/parameter_sources.md`.
Replace the [E] ranges in `sg_model.py`, rerun the scripts, and use real recordings for final
training and for any accuracy you report.

## Known limitations

- Lumped model. One coupling (his hand near the strap) comes from a 3D boundary-element
  calculation in `fem/`, confirmed with FastCap; the 3D solve is in air (no strap plastic or
  tissue), and where along the forearm he grips (1–5 cm from the strap) is an estimate. The other
  couplings are still geometry estimates.
- The passive static channel is simulated in time (`sg_passive.py`), but body voltages on Indian
  floors, her arm-movement statistics and how often a grab pulls her are estimates, not measured.
  With today's input and the ESP32 ADC it needs bodies at 10 V or more; the fused watch needs the
  bootstrapped input and an ADS1115.
- Event rates and durations in `event_stream.py` are guesses, not measured behaviour.
- Cause attribution in the prompt counts is approximate when long events overlap.
- The accelerometer is simulated from estimates (no published wrist data for grabs); no heart-rate
  or audio signals yet.
- Noise is Gaussian at the ADC; mains hum and radio bursts are not modelled explicitly.
