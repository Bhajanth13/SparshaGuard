# SparshaGuard: 2-minute explainer video

`SparshaGuard_demo_2min.mp4` (1:59, 1920×1080, captions only, no voice) introduces SparshaGuard to someone who has never seen it:
the problem (NCRB numbers), the idea, who made it, then the digital twin operated with a cursor in a Chrome window, the two pieces
of physics (capacitance, static electricity), where the numbers come from, the physics explorer, and where to try it.
A caption is on screen the whole time, the cards included.

Only the waiting is shortened: each caption segment is sped up to fit its text read at about 2.75 words a second (never more than 4×).
Short sounds mark the vibration, the alert and the cancels.

NCRB figures: *Crime in India 2022*, as reported in press coverage of the report: 4,45,256 crimes against women,
18.7 % assault on women with intent to outrage her modesty. 51 per hour = 4,45,256 / 8,760 hours. Check them against the
NCRB report itself before presenting.

## Captions

| Time | On screen | Caption |
|---|---|---|
| 0:00.0–0:04.9 | NCRB card: 4,45,256 crimes against women in 2022 (about 51 an hour); 18.7 % assaults to outrage modesty | In 2022, India registered 4,45,256 crimes against women: about 51 every hour. |
| 0:04.9–0:11.9 | NCRB card: 4,45,256 crimes against women in 2022 (about 51 an hour); 18.7 % assaults to outrage modesty | Nearly one in five was a grab or an unwanted touch. There's no time to unlock a phone. |
| 0:11.9–0:17.9 | Title card: SparshaGuard, co-developers Bhajanth V and Sukruth A Chinnur | SparshaGuard: a smartwatch that notices when another person touches her, and calls for help itself. |
| 0:17.9–0:22.7 | Title card: SparshaGuard, co-developers Bhajanth V and Sukruth A Chinnur | Designed by co-developers Bhajanth V and Sukruth A Chinnur, RV University, Mysuru. |
| 0:22.7–0:30.9 | Front page in Chrome; cursor points at the address, then opens the digital twin | The watch isn't built yet, so we made a digital twin: its real software on a simulated body. Try it here. |
| 0:30.9–0:37.9 | Digital twin, *Try it yourself* | Left: the wearer. Middle: her watch. Right: her emergency contact's phone. Tiles: things that can happen to her. |
| 0:37.9–0:42.8 | Digital twin, *Try it yourself* | She has turned on Guard Mode: the watch is watching for touches. |
| 0:42.8–0:49.1 | Digital twin, *Try it yourself* | Physics 1, capacitance: her body holds a little electric charge, and the watch measures how much. |
| 0:49.1–0:56.5 | Digital twin, *Try it yourself* | A stranger grabs her wrist. His body holds charge too: the reading jumps from 0.1 % to 16 %. |
| 0:56.5–1:02.5 | Digital twin, *Try it yourself* | The watch vibrates and asks for her PIN within 15 seconds. The mic starts recording. |
| 1:02.5–1:08.8 | Digital twin, *Try it yourself* | No PIN: her GPS location and the recording go to her contact, and 112 is called. |
| 1:08.8–1:14.4 | Digital twin, *Try it yourself* | What if he grabs her shoulder, far from the watch? Physics 2, static electricity. |
| 1:14.4–1:20.6 | Digital twin, *Try it yourself* | Every body carries static charge. Touching bodies share it in a microsecond, so her voltage jumps. |
| 1:20.6–1:25.5 | Digital twin, *Try it yourself* | This time it's a friend: she types her PIN, and it cancels. |
| 1:25.5–1:32.5 | Digital twin, *Try it yourself* | If she struggles, motion sensors feel the irregular jerks and ask for the PIN, even without a touch. |
| 1:32.5–1:37.8 | Digital twin, *Try it yourself* | Her own hand is the same body: no new charge, so no alarm. |
| 1:37.8–1:44.1 | Back to the front page; cursor opens the physics explorer | These numbers aren't guesses: every threshold comes from 60 published papers, checked with SPICE and FastCap. |
| 1:44.1–1:49.7 | Explorer, *Wrist grab* | The physics explorer shows, for any situation, whether the watch would notice, and why. |
| 1:49.7–1:53.5 | Explorer, References section | Every value is cited, like in a research paper. |
| 1:53.5–1:59.4 | End card: results and the website address | Try it at bhajanth13.github.io/SparshaGuard. Next: a real prototype. SparshaGuard: the touch itself raises the alarm. |

## How it is made

1. `python -m http.server 8800` in the repo root (the pages load from there; the omnibox shows the public address).
2. `node cards4.js` renders the NCRB, title and end cards.
3. `node session4.js`: Playwright records `wrapper4.html` (a Chrome-style frame with tabs, an omnibox, a cursor, a caption band and a
   card layer) and writes `timeline5.json` (caption and watch-status times). Re-run it if a detection is missed.
4. `python build_video4.py 2.75` cuts the take at the captions, speeds each segment to reading time, maps log times to video times
   (the recording's clock runs about 5 % slow) and adds the sounds.
