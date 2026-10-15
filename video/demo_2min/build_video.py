"""Cut the twin recording into a 2-minute video with cards, captions and event tones."""
import json, subprocess
d = json.load(open("timeline.json"))
VID, OFF = d["video"], 1.1          # recording time = log time - OFF
END = [e["t"] for e in d["log"] if e["ev"] == "end"][0]
CARDS_BEFORE = [("card_title.png", 4.5), ("card_ncrb1.png", 7.5), ("card_ncrb2.png", 9.0)]
CARD_END = ("card_end.png", 8.5)
lead = sum(s for _, s in CARDS_BEFORE)

CAPS = [
 (3.1, 4.3, "Ananya walks home alone. She turns on Guard Mode."),
 (4.3, 9.2, "The watch learns her body for 5 seconds (sped up)."),
 (9.2, 13.0, "Guarding: it senses touch 5 times a second."),
 (13.0, 17.5, "A stranger grabs her wrist: the touch signal jumps to 16 %, and her body's static jumps too."),
 (17.5, 27.5, "Held 2 s: the watch vibrates, asks for her PIN and turns the mic on. She can't answer."),
 (27.5, 32.5, "No PIN: her GPS location and voice recording go to her contacts. 112 is called."),
 (32.5, 37.3, "Guard Mode back on."),
 (37.3, 42.4, "A friend holds her hand: the PIN decides. She types 1234."),
 (42.4, 46.1, "Cancelled. The recording is deleted."),
 (46.1, 50.4, "Forced to cancel, she types her duress PIN: 9999."),
 (50.4, 56.1, "It shows \"Cancelled\", but Amma gets a silent alert."),
 (56.1, 60.5, "He rips the watch off: alert at once, no PIN."),
 (60.5, 65.3, "Guard Mode back on."),
 (65.3, 68.3, "A shoulder grab: the wrist sensor can't feel it, but the static jump and her pulled arm can."),
 (68.3, 73.1, "PIN prompt. (She cancels to continue.)"),
 (73.1, 82.5, "She struggles to get free: motion sensors detect it even with no touch. PIN prompt, mic on."),
 (82.5, 88.7, "Her own hand on the watch: no other body, ignored."),
 (88.7, 94.5, "Strap on a metal pole: not a person, ignored."),
 (94.5, 104.2, "A brush in a crowd, someone close: no pulling, no touch. Ignored."),
 (104.2, 110.3, "She runs for a bus: no alarm, but a touch now asks for the PIN."),
 (110.3, END, "9 simulated hours of daily life: 0–1 unwanted prompts (touch sensor alone: 24–28)."),
]
BORING = ("learns her body", "Guard Mode back on", "She can't answer")
def need(text): return len(text.split()) / 3.0 + 0.6      # reading time, ~3 words a second
SEGS = []                                                     # (log a, log b, speed, freeze s)
for a, b, text in CAPS:
    L, R = b - a, need(text)
    if L >= R:
        sp = min(4.0 if any(k in text for k in BORING) else 2.0, L / R)
        SEGS.append((a, b, sp, 0.0))
    else:
        SEGS.append((a, b, 1.0, R - L))                       # hold the last frame so the caption can be read
def seg_len(sg): return (sg[1] - sg[0]) / sg[2] + sg[3]
def out_t(t):                        # log time -> final video time (start of a hold counts as its segment end)
    acc = lead
    for sg in SEGS:
        a, b, sp, fz = sg
        if t <= a: return acc
        if t < b: return acc + (t - a) / sp
        acc += seg_len(sg)
    return acc
demo_len = sum(seg_len(sg) for sg in SEGS)
total = lead + demo_len + CARD_END[1]
print(f"demo {demo_len:.1f} s, total {total:.1f} s")
def ts(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f"{h}:{m:02d}:{s:05.2f}"
ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 0", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Cap,DejaVu Sans,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H50202A13,1,0,0,0,100,100,0,0,3,18,0,2,140,140,34,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
srt = []
starts = [lead]
for sg in SEGS: starts.append(starts[-1] + seg_len(sg))
for i, (a, b, text) in enumerate(CAPS, 1):
    s, e = starts[i - 1], starts[i]
    ass.append(f"Dialogue: 0,{ts(s)},{ts(e)},Cap,,0,0,0,,{text}")
    f = lambda x: ts(x).replace(".", ",").rjust(11, "0") + "0"
    srt.append(f"{i}\n{f(s)} --> {f(e)}\n{text}\n")
open("captions.ass", "w").write("\n".join(ass) + "\n")
open("captions.srt", "w").write("\n".join(srt))

# event tones on the final timeline
ev = [(e["t"], e["text"]) for e in d["log"] if e["ev"] == "status"]
tones = []
for t, s in ev:
    if s.startswith("Enter PIN"): tones.append((out_t(t), "buzz"))
    elif s.startswith("Alert sent"): tones.append((out_t(t), "siren"))
    elif s.startswith("Cancelled"): tones.append((out_t(t), "chime"))
for name, expr, dur in [("buzz", "0.35*sin(2*PI*170*t)*(lt(mod(t,0.3),0.12))", 0.6),
                        ("siren", "0.25*sin(2*PI*(660+220*lt(mod(t,0.5),0.25))*t)", 2.0),
                        ("chime", "0.3*sin(2*PI*660*t)*exp(-6*t)+0.3*sin(2*PI*990*t)*exp(-6*t)*gte(t,0.12)", 0.8)]:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={dur}", f"{name}.wav"], check=True)

# video: cards + demo segments, 30 fps
inputs, parts = [], []
for i, (img, dur) in enumerate(CARDS_BEFORE):
    inputs += ["-loop", "1", "-t", str(dur), "-i", img]
    parts.append(f"[{i}:v]fps=30,format=yuv420p,setsar=1[c{i}]")
nb = len(CARDS_BEFORE)
inputs += ["-i", VID]
vi = nb
for k, (a, b, sp, fz) in enumerate(SEGS):
    hold = f",tpad=stop_mode=clone:stop_duration={fz:.2f}" if fz > 0 else ""
    parts.append(f"[{vi}:v]trim={a - OFF:.3f}:{b - OFF:.3f},setpts=(PTS-STARTPTS)/{sp:.4f},fps=30{hold},scale=1766:994,pad=1920:1080:77:4:color=0xeef1f4,format=yuv420p,setsar=1[s{k}]")
inputs += ["-loop", "1", "-t", str(CARD_END[1]), "-i", CARD_END[0]]
ei = vi + 1
parts.append(f"[{ei}:v]fps=30,format=yuv420p,setsar=1[ce]")
# fades on the cards
order = [f"[c{i}]" for i in range(nb)] + [f"[s{k}]" for k in range(len(SEGS))] + ["[ce]"]
parts.append("".join(order) + f"concat=n={len(order)}:v=1:a=0[cat]")
parts.append("[cat]subtitles=captions.ass[vout]")
# audio
ai = ei + 1
amix = []
for j, (t, name) in enumerate(tones):
    inputs += ["-i", f"{name}.wav"]
    amix.append(f"[{ai + j}:a]adelay={int(t * 1000)}|{int(t * 1000)}[a{j}]")
if amix:
    parts += amix
    parts.append("".join(f"[a{j}]" for j in range(len(tones))) + f"amix=inputs={len(tones)}:normalize=0,apad,atrim=0:{total:.2f}[aout]")
cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
       "-movflags", "+faststart", "-t", f"{total:.2f}", "SparshaGuard_demo_2min.mp4"]
subprocess.run(cmd, check=True)
print("tones", len(tones))
