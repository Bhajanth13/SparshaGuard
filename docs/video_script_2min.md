# SparshaGuard: 2-minute video script

Built around the demo's **Play all** run (about 115 s, timings measured in the browser), with a
short intro before it and one closing line after it. Narration is about 150 words a minute; the
on-screen captions already say the key facts, so the voice can be calm and brief.

## Setup before recording

1. Open `demo/sparshaguard_demo.html` in Chrome, press F11 for full screen, sound on.
2. Have a title slide ready (SparshaGuard logo, team names, RV University).
3. Start the screen recorder (Windows: Win + Alt + R or OBS; Mac: Cmd + Shift + 5).

## Script

| Time | On screen | Narration |
|---|---|---|
| 0:00–0:07 | Title slide | "Most safety apps need her to find her phone and press SOS. In an attack, there's no time." |
| 0:07–0:10 | Demo page, idle (science panel open). Click **Play all** at 0:10 | "SparshaGuard flips the default: someone else's touch raises the alarm." |
| 0:10–0:18 | Ch 1: Guard Mode, watch learns, then "Guarding" | "Ananya turns on Guard Mode. The watch learns her own body for five seconds." |
| 0:18–0:40 | Ch 2: stranger grabs her wrist; both charts jump; PIN countdown; alert; Amma's phone | "A stranger grabs her wrist. The sensor signal jumps, and so does her body's static: another body touched her. She can't answer the PIN, so her location goes out, 112 is called, audio is recorded." |
| 0:40–0:53 | Re-arm, then Ch 3: friend holds her hand, PIN 1234, Cancelled | "A friend's hand is another body too, so the PIN decides. Cancelled." |
| 0:53–1:04 | Ch 4: forced to cancel, PIN 9999, silent alert on the phone | "Forced to cancel? Her duress PIN shows 'Cancelled', but her mother still gets a silent alert." |
| 1:04–1:13 | Ch 5: the watch is ripped off, alert in under a second | "Rip the watch off, and it alerts at once." |
| 1:13–1:22 | Ch 6: shoulder grab; static jump, arm jerks, PIN prompt | "A grab on her shoulder: the wrist sensor can't feel it, but her body's charge jumps the instant he touches her, and the watch feels her arm being pulled." |
| 1:22–1:30 | Ch 7: she struggles to get free; PIN prompt, mic on | "If she fights back, the accelerometer and gyroscope feel the struggle, and the microphone turns on." |
| 1:30–1:52 | Ch 8: her own hand, metal pole, a brush, someone close, she runs: all ignored | "Her own hand, a metal pole, a brush in a crowd, running for a bus: none of them sets it off. In nine simulated hours: one unwanted prompt, against twenty-four for a sweep-only watch." |
| 1:52–2:00 | Title slide again | "Physics from published papers, checked with SPICE and FastCap. Next, a prototype to measure it. SparshaGuard: the touch itself is the alarm." |

## Tips

- Play all now runs about 115 s (eight chapters). To fit 2:00, shorten the title slide to 4 s, start
  Play all at 0:05, and in editing trim the 15 s PIN countdown in chapter 2 and the re-learning pauses.

- If a chapter runs a little long, trim the pause after the alert in editing rather than rushing
  the voice.
- Record the demo once without narration, then record the voice over it; it is easier to time.
- Open "Show the science" before pressing Play all, so the firmware log and the four numbers are
  on screen throughout.
- If asked about limits: static levels on Indian floors and how often a grab pulls her arm are
  estimates until the prototype measures them; a grab that only holds is missed away from the wrist.
