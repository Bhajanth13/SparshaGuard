# Second ground: can a separately grounded node see a touch anywhere?

Study: `simulation/second_ground.py` (run in about 1 minute). Figures:
`results/figures/fig20_second_ground.png`, `results/figures/fig21_second_ground_coupling.png`.
Numbers: `results/data/second_ground_results.json`. Interactive: question 6 in the explorer.

## The question

The watch on its own floats with her body. A stranger touching her shoulder doubles her body's
capacitance to the surroundings (about 140 pF → 280 pF), but the watch sees that only through its
own ~1 pF return path, so the sweep changes by about 0.02 % (`whole_body_detection.md`). The passive
static channel sees a touch anywhere, but only when the two bodies differ in charge by more than about
1.6 V (`consistency_pass_2026-11-06.md`).

The whole-body research (7 Nov 2026) found one family of ideas that does not depend on charge: give
the system a **second electrical reference** the watch does not share. Here the watch sends its
usual small signal into her skin through E1, and a second receiver with its **own battery and
floating ground** measures her body against that ground. Published two-node body-channel models
(Maity et al. 2018; Das et al. 2020) predict that a second person in firm contact roughly halves the
received signal, wherever the touch lands. A receiver that shares the watch's ground cannot see this:
the effect cancels.

Candidate places for the second node: inside the strap clasp under the wrist (nothing extra to
wear), a pendant at the collarbone, an anklet.

## The model

`second_ground.py` extends the nodal network of `sg_model.py` (watch tank S, her body B, the other
person A, the surroundings E, all against the watch ground 0) with two nodes:

| Node / branch | Value | Source |
|---|---|---|
| R: the node's 1–2 cm² steel pad on her skin | `z_electrode` of the model | [S10] |
| R–K: receiver input | 1 MΩ ∥ 10 pF | [E] |
| B–K: the node's board over her skin | plate, er 2–3, 2–4 cm², 1.5–3 mm | [G] |
| K–E: the node's return path to the surroundings | clasp 0.15–0.8 pF, pendant 0.3–1.5 pF, anklet 1–5 pF | [G/S11, E] |
| **K–0: direct coupling between the two grounds, C_K0** | clasp with E2 kept 15 mm clear 0.05–0.5 pF; clasp with E2 running up to it 0.5–3 pF; pendant 0.005–0.05 pF; anklet 0.001–0.01 pF | [E] |
| A–K: the other person to the node | his coupling to the watch × (node return / watch return) | [E] |

Tone: 200 kHz from E1 (inside the MAX30009 and AD5940 ranges). Events reuse the model's own
contacts: a stranger's hand (40–80 cm², bare or through cloth) at the shoulder, waist, face/hair,
other arm and wrist; an earthed railing in her hand; a phone; a bystander 30 cm away. Added for this
study [E]: she sits down (her capacitance to the floor ×1.2–1.8), she walks past a wall or car (every
return path +10 %), and the node wobbles against the watch (C_K0 ±3 % for a clasp, ±50 % for a pendant
or anklet as the arm swings; its board-to-skin coupling ±10 %). 4,500 cases per event (street shoes,
sandals, barefoot on tile).

## What it found

**1. The direct coupling between the two grounds decides everything** (fig 21). The watch drives her
body hard against its own ground, so the node sees a large, steady signal through C_K0 that has
nothing to do with the touch. The touch only changes the small part that runs through the
surroundings. The published models leave C_K0 out. For a typical person, a shoulder touch is 3× larger
than a 3 % wobble of C_K0 only while **C_K0 stays below about 0.01 pF**.

**2. In the clasp, the grounds are too close** (fig 20). Median change for a touch away from the wrist:

| Second node | Shoulder | Hair | Railing | Sits down | Wall / car | Node wobble |
|---|---|---|---|---|---|---|
| Watch's own ground (no second node) | 0.16 % | 0.17 % | 0.01 % | 0.00 % | 0.15 % | 0.15 % |
| Clasp, E2 kept 15 mm clear | 0.9 % | 1.0 % | 1.4 % | 0.4 % | 0.2 % | 1.5 % |
| Clasp, E2 runs up to it | 0.5 % | 0.5 % | 0.2 % | 0.1 % | 0.3 % | 2.2 % |
| Pendant at the collarbone | 6.8 % | 9.2 % | 21 % | 6.5 % | 3.0 % | 18 % |
| Anklet | 25 % | 34 % | 80 % | 25 % | 12 % | 4.0 % |

(Median of the size of the change. Watch's own ground at 200 kHz; the full sweep score is lower.)

**3. Share of touches away from the wrist that stand out** from everyday drift (more than twice its
95th percentile):

| Second node | She is still | She is moving | Railing (still) | Sits down (still) |
|---|---|---|---|---|
| Watch's own ground | 0 % | 0 % | 0 % | 0 % |
| Clasp, E2 kept clear | 34 % | 0 % | 54 % | 14 % |
| Clasp, E2 close | 6 % | 0 % | 1 % | 0 % |
| Pendant | 18 % | 0 % | 66 % | 11 % |
| Anklet | 52 % | 50 % | 100 % | 37 % |

**4. It is not a clear sign on its own.** A second ground answers "did her body just connect to
something big?", not "was it a person?". Holding an earthed railing and sitting down change it as
much as a stranger's hand, in every placement. It also responds to changes in the surroundings, which
the watch alone mostly ignores.

## What it means for the design

- **Clasp (nothing extra to wear):** works only if C_K0 is a few hundredths of a pF and the clasp is
  rigid. Then about a third of far touches stand out while she stands still, and almost none while she
  moves. E2 must stop well short of the clasp, and the clasp's ground plane must face away from the
  strap ends. Marginal.
- **Pendant:** the coupling is small enough, but the pendant moves against the watch whenever her arm
  moves, which swamps the touch. It needs the IMU to ignore changes that come with arm movement, and it
  only helps while her arm is still.
- **Anklet:** the strongest and steadiest signal, but railings and sitting look the same.
- **Best use:** a second ground is a useful extra clue, combined with the others. A sudden drop with no
  arm movement (IMU), no grab of an object (her hand stays still), and either a static step or a skin
  response 1–4 s later points to a person. It covers the case the static channel misses: two people at
  the same potential.

None of this is measured. C_K0, the node's return path and its wobble are estimates [E].

## Gate 1 test (added to `SparshaGuard-Gate1/docs/04_test_protocol.md`, E11)

1. Battery receiver (MAX30009 or an AD9833-band lock-in on an ESP32 ADC) with its own cell and a 1–2 cm²
   steel pad, under the clasp; the watch transmits 200 kHz from E1.
2. Measure C_K0 directly (LCR meter between the two grounds, band worn) for: E2 running to the clasp,
   E2 stopped 15 mm short, E2 stopped 30 mm short. Then move the receiver to the collarbone.
3. Record the received amplitude for: stranger touches at the shoulder, back, hair and other arm (bare
   and through cloth), earthed railing, sitting down, walking past a wall, a bystander at 30 cm, and arm
   swinging with nobody touching.
4. Compare with fig 20: if far touches stand out from the wobble while still and moving, the clasp
   node goes into the design; if only while still, it becomes a confirmation clue.
