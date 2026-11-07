"""Edit the cursor-driven Chrome recording into a calm 2-minute video: cards, timed segments, tones."""
import json, re, subprocess, sys
import numpy as np
d = json.load(open("timeline5.json"))
VID, log = d["video"], d["log"]
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VID]))
END = [e["t"] for e in log if e["ev"] == "end"][0]
# The recording's clock runs about 5 % slow against the log, so map log times to video times through anchors:
# the frame where each caption band changes (scene detection; skips the encoder's 5.12 s keyframe blips).
sc = subprocess.run(["ffmpeg", "-v", "error", "-i", VID, "-vf", "crop=1920:120:0:960,scale=192:12,format=gray,select='gt(scene,0.01)',metadata=print:file=-",
                     "-f", "null", "-"], capture_output=True, text=True).stdout
chg = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", sc)]
chg = [x for x in chg if abs(x / 5.12 - round(x / 5.12)) * 5.12 > 0.06]
caps = [e["t"] for e in log if e["ev"] == "caption"]
slope = (dur - caps[0]) / (END - caps[0])
A_LOG, A_VID = [0.0], [0.0]
for t in caps:
    guess = A_VID[-1] + (t - A_LOG[-1]) * slope
    near = [x for x in chg if guess - 1.5 < x < guess + 2.0 and x > A_VID[-1] + 1]
    if near: A_LOG.append(t); A_VID.append(min(near, key=lambda x: abs(x - guess)) - 0.05)
A_LOG.append(END); A_VID.append(dur)
def V(t): return float(np.interp(t, A_LOG, A_VID))
print("anchors", [(round(a, 1), round(b - a, 2)) for a, b in zip(A_LOG, A_VID)])
WPS = float(sys.argv[1]) if len(sys.argv) > 1 else 2.4    # calm reading speed, words per second
cut = [e for e in log if e["ev"] in ("start", "caption")] + [{"t": END, "ev": "end"}]
SEGS = []
for a, b in zip(cut, cut[1:]):
    L = V(b["t"]) - V(a["t"])
    R = len(a.get("text", "").split()) / WPS + 0.5 if a["ev"] == "caption" else max(L, 1e-3)
    SEGS.append((V(a["t"]), V(b["t"]), max(1.0, min(4.0, L / R))))
CARDS = []                                                # the cards are inside the recording, under captions
lead = sum(x for _, x in CARDS)
def out_t(t):
    t = V(t); acc = lead
    for a, b, sp in SEGS:
        if t <= a: return acc
        if t < b: return acc + (t - a) / sp
        acc += (b - a) / sp
    return acc
demo = sum((b - a) / sp for a, b, sp in SEGS)
total = lead + demo
print(f"words/s {WPS}: demo {demo:.1f} s, total {total:.1f} s")
if "--plan" in sys.argv: sys.exit()
tones = []
for e in log:
    if e["ev"] != "status": continue
    s = e["text"]
    if s.startswith("Enter PIN") and "15 s" in s: tones.append((out_t(e["t"]), "buzz"))
    elif s.startswith("Alert sent"): tones.append((out_t(e["t"]), "siren"))
    elif s.startswith("Cancelled"): tones.append((out_t(e["t"]), "chime"))
# each segment is rendered on its own (one graph with 20+ trims of the same input runs out of memory), then joined
import os
os.makedirs("segs4", exist_ok=True); lst = []
for k, (a, b, sp) in enumerate(SEGS):
    if b - a < 0.02: continue
    out = f"segs4/s{k:02d}.mp4"; lst.append(f"file '{out}'")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", VID,
                    "-vf", f"setpts=(PTS-STARTPTS)/{sp:.4f},fps=30,format=yuv420p,setsar=1", "-an", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "18", out], check=True)
open("segs4/list.txt", "w").write("\n".join(lst).replace("segs4/", ""))
inputs = ["-f", "concat", "-safe", "0", "-i", "segs4/list.txt"]; parts = ["[0:v]fade=t=in:st=0:d=0.5[vout]"]
for j, (t, name) in enumerate(tones):
    inputs += ["-i", f"{name}.wav"]; parts.append(f"[{1 + j}:a]adelay={int(t * 1000)}|{int(t * 1000)}[a{j}]")
parts.append("".join(f"[a{j}]" for j in range(len(tones))) + f"amix=inputs={len(tones)}:normalize=0,apad,atrim=0:{total:.2f}[aout]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-t", f"{total:.2f}", "SparshaGuard_demo_2min.mp4"], check=True)
json.dump({"segments": SEGS, "lead": lead, "total": total, "captions": [(round(out_t(e["t"]), 2), e["text"]) for e in log if e["ev"] == "caption"]},
          open("edit_plan.json", "w"), indent=1)
print("tones", len(tones))
