# SparshaGuard: 2-minute demonstration video

`SparshaGuard_demo_2min.mp4` (1:59, 1920×1080) is a screen recording of the digital twin's guided story,
with slow stretches sped up (re-learning, the 15 s countdown) and short holds so every caption can be read (about 3 words a second), title and NCRB cards, burned-in captions and
event sounds (vibration at each PIN prompt, a siren on alerts, a chime on cancel). It has no voice-over: the
narration below is timed to the video, for the team to record over it. `captions.srt` holds the same captions
for platforms that show subtitles.

NCRB figures: *Crime in India 2022* (as reported in press coverage of the report): 4,45,256 crimes against
women (4,28,278 in 2021, +4 %), 66.4 per lakh women, 18.7 % assault on women with intent to outrage her
modesty, 19.2 % kidnapping and abduction. 51 per hour = 4,45,256 / 8,760 hours.

| Time | On screen | Caption / narration |
|---|---|---|
| 0:00–0:04 | Title card: SparshaGuard, Team Sparsha, RV University, Mysuru | SparshaGuard: a safety smartwatch where a stranger's touch raises the alarm. |
| 0:04–0:12 | NCRB card: 4,45,256 crimes against women in 2022 | In 2022, India registered 4,45,256 crimes against women: about 51 every hour, up 4 % on the year before. |
| 0:12–0:21 | NCRB card: 18.7 % assaults on modesty; 19.2 % kidnapping | Almost one in five were assaults to outrage a woman's modesty: a grab, an unwanted touch. In that moment there is no time to unlock a phone. SparshaGuard flips it: the touch itself raises the alarm. |
| 0:21–0:24 | Digital twin | Ananya walks home alone. She turns on Guard Mode. |
| 0:24–0:28 | Digital twin | The watch learns her body for 5 seconds (sped up). |
| 0:28–0:31 | Digital twin | Guarding: it senses touch 5 times a second. |
| 0:31–0:38 | Digital twin | A stranger grabs her wrist: the touch signal jumps to 16 %, and her body's static jumps too. |
| 0:38–0:45 | Digital twin | Held 2 s: the watch vibrates, asks for her PIN and turns the mic on. She can't answer. |
| 0:45–0:50 | Digital twin | No PIN: her GPS location and voice recording go to her contacts. 112 is called. |
| 0:50–0:52 | Digital twin | Guard Mode back on. |
| 0:52–0:56 | Digital twin | A friend holds her hand: the PIN decides. She types 1234. |
| 0:56–0:59 | Digital twin | Cancelled. The recording is deleted. |
| 0:59–1:02 | Digital twin | Forced to cancel, she types her duress PIN: 9999. |
| 1:02–1:06 | Digital twin | It shows "Cancelled", but Amma gets a silent alert. |
| 1:06–1:10 | Digital twin | He rips the watch off: alert at once, no PIN. |
| 1:10–1:12 | Digital twin | Guard Mode back on. |
| 1:12–1:18 | Digital twin | A shoulder grab: the wrist sensor can't feel it, but the static jump and her pulled arm can. |
| 1:18–1:21 | Digital twin | PIN prompt. (She cancels to continue.) |
| 1:21–1:27 | Digital twin | She struggles to get free: motion sensors detect it even with no touch. PIN prompt, mic on. |
| 1:27–1:31 | Digital twin | Her own hand on the watch: no other body, ignored. |
| 1:31–1:35 | Digital twin | Strap on a metal pole: not a person, ignored. |
| 1:35–1:39 | Digital twin | A brush in a crowd, someone close: no pulling, no touch. Ignored. |
| 1:39–1:45 | Digital twin | She runs for a bus: no alarm, but a touch now asks for the PIN. |
| 1:45–1:50 | Digital twin | 9 simulated hours of daily life: 0–1 unwanted prompts (touch sensor alone: 24–28). |
| 1:50–1:59 | End card: results and live link | On the digital twin: 70 % of grabs caught anywhere on her body, 99 % of struggles, and at most one unwanted prompt in nine hours. Simulated from 60 published sources; next, a battery-powered prototype. |

## Rebuild

```bash
node record.js          # records the guided story in Chromium (about 2 min) -> *.webm + timeline.json
node cards.js          # renders the title, NCRB and end cards
python build_video.py  # cuts, speeds up, captions and adds tones -> SparshaGuard_demo_2min.mp4
```
The cut points in `build_video.py` are times in `timeline.json`; check them after a new recording.
