# SparshaGuard: 2-minute demonstration video

`SparshaGuard_demo_2min.mp4` (1:57, 1920×1080, captions only, no voice) is a single take in a Chrome window. A cursor
starts on the project's front page, where the co-developers introduce themselves (Bhajanth V and Sukruth A Chinnur,
RV University, Mysuru) and point to the website, opens the digital twin in a new tab and operates it (*Try it yourself*: tiles, PIN on
the watch), then goes back to the front page, opens the physics explorer and scrolls to its 60 references.
Two captions explain the physics as it happens: capacitance (the wrist grab) and static electricity (the shoulder grab).

Only the waiting is shortened: each caption segment is sped up to fit its text read at about 2.8 words a second (never more
than 4×). Short sounds mark the vibration, alerts and cancels.

NCRB figures: *Crime in India 2022*, as reported in press coverage of the report: 4,45,256 crimes against women,
18.7 % assault on women with intent to outrage her modesty. 51 per hour = 4,45,256 / 8,760 hours. Check them against the
NCRB report itself before presenting.

## Captions

| Time | On screen | Caption |
|---|---|---|
| 0:00.0–0:09.0 | NCRB card: 4,45,256 crimes against women in 2022 (about 51 an hour); 18.7 % assaults to outrage modesty; "In that moment there is no time to unlock a phone and press SOS. SparshaGuard flips it: the touch itself raises the alarm." | (card text) |
| 0:12.0–0:18.2 | Front page in Chrome | Hi! We are Bhajanth V and Sukruth A Chinnur, co-developers of SparshaGuard at RV University, Mysuru. |
| 0:18.2–0:24.1 | Front page in Chrome | Everything here is live at bhajanth13.github.io/SparshaGuard: anyone can try the digital twin and the explorer. |
| 0:24.1–0:30.6 | Digital twin, *Try it yourself* | The digital twin runs the watch's own firmware on a simulated sensor. We switch Guard Mode on. |
| 0:30.6–0:36.8 | Digital twin, *Try it yourself* | Physics 1, capacitance: the watch sweeps 200 frequencies through a skin electrode, five times a second. |
| 0:36.8–0:43.4 | Digital twin, *Try it yourself* | A stranger grabs her wrist: the watch vibrates, asks for a PIN, and the mic turns on. |
| 0:43.4–0:49.6 | Digital twin, *Try it yourself* | Capacitance: his hand closes a path back to the watch. Signal: 0.1 % → 16 %. |
| 0:49.6–0:56.2 | Digital twin, *Try it yourself* | No PIN: her location and the voice recording go to her emergency contact, and 112 is called. |
| 0:56.2–0:58.5 | Digital twin, *Try it yourself* | Guard Mode back on. |
| 0:58.5–1:05.8 | Digital twin, *Try it yourself* | Physics 2, static electricity: every body carries charge. Touching bodies share it within a microsecond, so her voltage jumps. |
| 1:05.8–1:11.7 | Digital twin, *Try it yourself* | She cancels with her PIN; a duress PIN would cancel on screen but alert silently. |
| 1:11.7–1:20.4 | Digital twin, *Try it yourself* | That grab was on her shoulder: too far for the capacitive sensor, but the static jump and her pulled arm gave it away. |
| 1:20.4–1:27.7 | Digital twin, *Try it yourself* | She struggles to get free: the accelerometer and gyroscope see irregular jerks. A PIN prompt, even without a touch. |
| 1:27.7–1:33.9 | Digital twin, *Try it yourself* | Her own hand on the watch is the same body: no static jump, so no alarm. |
| 1:33.9–1:39.8 | Front page → explorer | Every threshold and value comes from published research: 60 sources, checked with SPICE and FastCap. |
| 1:39.8–1:46.7 | Explorer, *Her own hand* preset | The explorer runs the same physics: pick a situation and see whether the watch would notice, and why. |
| 1:46.7–1:51.8 | Explorer, References section | Each value is cited like a research paper: these are the 60 references. |
| 1:51.8–1:57.3 | End card: 70 % of grabs, 99 % of struggles, 0–1 unwanted prompts in 9 h, 100 % of strap removals; bhajanth13.github.io/SparshaGuard | (card text) |

## How it is made

1. `python -m http.server 8800` in the repo root (the pages load from there; the omnibox shows the public address).
2. `node session3.js`: Playwright records `wrapper3.html` (a Chrome-style frame with tabs, an omnibox and a cursor) and writes
   `timeline4.json` (caption and watch-status times). It re-takes itself if a detection is missed.
3. `node cards.js` renders the NCRB and end cards; `python build_video3.py 2.8` cuts the take at the captions, speeds each segment
   to reading time, maps log times to video times (the recording's clock runs about 5 % slow), adds the cards and sounds.
