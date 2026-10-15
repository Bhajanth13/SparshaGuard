"""Edit the cursor-driven Chrome recording into a calm 2-minute video: cards, timed segments, tones."""
import json, subprocess, sys
d = json.load(open("timeline3.json"))
VID, log = d["video"], d["log"]
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VID]))
END = [e["t"] for e in log if e["ev"] == "end"][0]
OFF = -0.4                                                # measured: first caption appears 0.4 s later in the video than in the log
WPS = float(sys.argv[1]) if len(sys.argv) > 1 else 2.4    # calm reading speed, words per second
cut = [e for e in log if e["ev"] in ("start", "caption")] + [{"t": END, "ev": "end"}]
SEGS = []
for a, b in zip(cut, cut[1:]):
    L = b["t"] - a["t"]
    R = len(a.get("text", "").split()) / WPS + 0.5 if a["ev"] == "caption" else L
    SEGS.append((a["t"], b["t"], max(1.0, min(3.0, L / R))))
CARDS = [("card_title.png", 4.5), ("card_ncrb.png", 10.0)]
CARD_END = ("card_end.png", 7.0)
lead = sum(x for _, x in CARDS)
def out_t(t):
    acc = lead
    for a, b, sp in SEGS:
        if t <= a: return acc
        if t < b: return acc + (t - a) / sp
        acc += (b - a) / sp
    return acc
demo = sum((b - a) / sp for a, b, sp in SEGS)
total = lead + demo + CARD_END[1]
print(f"words/s {WPS}: demo {demo:.1f} s, total {total:.1f} s, offset {OFF:.2f}")
if "--plan" in sys.argv: sys.exit()
tones = []
for e in log:
    if e["ev"] != "status": continue
    s = e["text"]
    if s.startswith("Enter PIN") and "15 s" in s: tones.append((out_t(e["t"]), "buzz"))
    elif s.startswith("Alert sent"): tones.append((out_t(e["t"]), "siren"))
    elif s.startswith("Cancelled"): tones.append((out_t(e["t"]), "chime"))
inputs, parts = [], []
for i, (img, x) in enumerate(CARDS):
    inputs += ["-loop", "1", "-t", str(x), "-i", img]
    parts.append(f"[{i}:v]fps=30,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.4,fade=t=out:st={x - 0.4}:d=0.4[c{i}]")
vi = len(CARDS); inputs += ["-i", VID]
for k, (a, b, sp) in enumerate(SEGS):
    parts.append(f"[{vi}:v]trim={a - OFF:.3f}:{b - OFF:.3f},setpts=(PTS-STARTPTS)/{sp:.4f},fps=30,format=yuv420p,setsar=1[s{k}]")
ei = vi + 1; inputs += ["-loop", "1", "-t", str(CARD_END[1]), "-i", CARD_END[0]]
parts.append(f"[{ei}:v]fps=30,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.4[ce]")
order = [f"[c{i}]" for i in range(len(CARDS))] + [f"[s{k}]" for k in range(len(SEGS))] + ["[ce]"]
parts.append("".join(order) + f"concat=n={len(order)}:v=1:a=0[vout]")
ai = ei + 1
for j, (t, name) in enumerate(tones):
    inputs += ["-i", f"{name}.wav"]; parts.append(f"[{ai + j}:a]adelay={int(t * 1000)}|{int(t * 1000)}[a{j}]")
parts.append("".join(f"[a{j}]" for j in range(len(tones))) + f"amix=inputs={len(tones)}:normalize=0,apad,atrim=0:{total:.2f}[aout]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-t", f"{total:.2f}", "SparshaGuard_demo_2min.mp4"], check=True)
json.dump({"segments": SEGS, "lead": lead, "total": total, "captions": [(round(out_t(e["t"]), 2), e["text"]) for e in log if e["ev"] == "caption"]},
          open("edit_plan.json", "w"), indent=1)
print("tones", len(tones))
