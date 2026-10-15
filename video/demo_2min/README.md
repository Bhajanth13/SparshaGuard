# SparshaGuard: 2-minute demonstration video

`SparshaGuard_demo_2min.mp4` (1:57, 1920×1080) is a single take of the digital twin operated in a Chrome
window: a cursor switches to *Try it yourself*, presses the touch tiles, types the PIN on the watch and points at
the signals and the phone while captions explain each step. Only the waiting is shortened: each caption segment
is sped up to fit its text read at about 2.2 words a second (never more than 3×). Title and NCRB cards open it,
a results card closes it, and short sounds mark the vibration, alerts and cancels. It has no voice-over; the
narration below is timed to the video for the team to record over it.

NCRB figures: *Crime in India 2022*, as reported in press coverage of the report: 4,45,256 crimes against women
(4,28,278 in 2021, +4 %), 18.7 % assault on women with intent to outrage her modesty. 51 per hour = 4,45,256 /
8,760 hours. Check them against the NCRB report itself before presenting.

| Time | On screen | Caption / narration |
|---|---|---|
| 0:00.0–0:04.5 | Title card: SparshaGuard · Team Sparsha, RV University, Mysuru · co-developers Bhajanth V and Sukruth A Chinnur | SparshaGuard: a safety smartwatch where a stranger's touch raises the alarm. |
| 0:04.5–0:14.5 | NCRB card: 4,45,256 crimes against women in 2022 (about 51 an hour); 18.7 % assaults to outrage modesty | In 2022, India registered 4,45,256 crimes against women: about 51 every hour. Almost one in five were assaults to outrage a woman's modesty: a grab, an unwanted touch. In that moment there is no time to unlock a phone. SparshaGuard flips it: the touch itself raises the alarm. |
| 0:16.1–0:21.6 | Digital twin in Chrome (cursor operates it) | SparshaGuard's digital twin: the watch's own firmware, running live in Chrome. |
| 0:21.6–0:26.6 | Digital twin in Chrome (cursor operates it) | Guard Mode on: the watch first learns the wearer's body. |
| 0:26.6–0:31.2 | Digital twin in Chrome (cursor operates it) | Guarding. The touch signal stays flat, inside the noise. |
| 0:31.2–0:34.0 | Digital twin in Chrome (cursor operates it) | A stranger grabs her wrist. |
| 0:34.0–0:39.0 | Digital twin in Chrome (cursor operates it) | The touch signal jumps from 0.1 % to 16 %… |
| 0:39.0–0:43.9 | Digital twin in Chrome (cursor operates it) | …and her static voltage jumps: another person's body touched her. |
| 0:43.9–0:50.9 | Digital twin in Chrome (cursor operates it) | Held 2 seconds: the watch vibrates, asks for a PIN, and the mic turns on. |
| 0:50.9–0:58.7 | Digital twin in Chrome (cursor operates it) | No PIN: her location and the voice recording go to her emergency contact. 112 is called. |
| 0:58.7–1:01.0 | Digital twin in Chrome (cursor operates it) | Guard Mode back on. |
| 1:01.0–1:07.6 | Digital twin in Chrome (cursor operates it) | A friend holds her hand. Every hand is another body to the sensor, so the PIN decides. |
| 1:07.6–1:12.2 | Digital twin in Chrome (cursor operates it) | She types 1234: cancelled, and the recording is deleted. |
| 1:12.2–1:16.8 | Digital twin in Chrome (cursor operates it) | Forced to cancel? She types the duress PIN, 9999. |
| 1:16.8–1:22.3 | Digital twin in Chrome (cursor operates it) | It shows "Cancelled", but her emergency contact gets a silent alert. |
| 1:22.3–1:26.8 | Digital twin in Chrome (cursor operates it) | A shoulder grab: the wrist sensor can't feel it… |
| 1:26.8–1:31.3 | Digital twin in Chrome (cursor operates it) | …but the static jump and her pulled arm can. PIN prompt. |
| 1:31.3–1:34.3 | Digital twin in Chrome (cursor operates it) | She cancels to continue. |
| 1:34.3–1:39.4 | Digital twin in Chrome (cursor operates it) | She struggles to get free: motion sensors see irregular, violent jerks. |
| 1:39.4–1:44.4 | Digital twin in Chrome (cursor operates it) | PIN prompt and mic on, even with no touch felt. |
| 1:44.4–1:50.4 | Digital twin in Chrome (cursor operates it) | Her own hand on the watch: same body, no static jump. Ignored. |
| 1:50.4–1:57.4 | End card: results and live link | On the digital twin: 70 % of grabs caught anywhere on her body, 99 % of struggles, and at most one unwanted prompt in nine hours. Simulated from 60 published sources; next, a battery-powered prototype. |

## Rebuild

```bash
python -m http.server 8800 --directory <repo root> &   # the twin must be served over http
node session2.js        # the scripted session in a Chrome-style window, recorded -> rec/*.webm + timeline3.json
node cards.js           # title, NCRB and results cards
python build_video2.py 2.2   # edit at 2.2 words a second -> SparshaGuard_demo_2min.mp4
```
