# SparshaGuard: 3.5-minute presentation script

Two speakers, about 1:45 each, with the deck `docs/SparshaGuard_BIH2026.pptx` (9 slides) on screen.
Bhajanth opens and explains the idea and how it works (slides 1–4); Sukruth shows it working and closes (slides 5–9).
About 490 spoken words in total, at a calm 140 words a minute. **[Next]** marks a slide change.

---

## Bhajanth V: slides 1–4 (about 1:45)

**Slide 1: Title** (0:00–0:12)

> Good morning. I'm Bhajanth, and this is Sukruth. We're Team Sparsha from RV University, Mysuru, and this is
> SparshaGuard: a safety smartwatch where a stranger's touch raises the alarm. **[Next]**

**Slide 2: Problem Statement** (0:12–0:35)

> In 2022, India registered over four lakh forty-five thousand crimes against women: about 51 every hour.
> Nearly one in five was a grab or an unwanted touch.
> Yet every safety tool today, an SOS app or a panic button, needs the victim to act first.
> In an attack, there is rarely time. **[Next]**

**Slide 3: Proposed Solution** (0:35–1:08)

> So we flipped it: the watch notices another person's touch by itself.
> In normal mode, it's just a watch. When she feels unsafe, she turns on Guard Mode.
> Now, if a stranger grabs her, or she struggles to get free, the watch vibrates, asks for her PIN within
> 15 seconds and starts recording.
> Her real PIN cancels it. No PIN, and her location and the recording go to her family, and 112 is called.
> And if she's forced to cancel, a duress PIN shows "Cancelled" but alerts them silently. **[Next]**

**Slide 4: Architecture & Technology** (1:08–1:48)

> How does a watch know it's another person? Two pieces of physics.
> First, capacitance: the watch sends tiny signals through her skin, and another person's hand changes them sharply.
> Second, static electricity: every body carries charge, and when two bodies touch, it evens out in a microsecond,
> so her voltage jumps. Her own hand or a metal pole can't do that.
> Every value comes from 60 published papers, and we cross-checked the physics with two independent solvers.
> Sukruth will show you it working. **[Next]**

---

## Sukruth A Chinnur: slides 5–9 (about 1:45)

**Slide 5: Prototype & Demonstration** (1:48–2:20)

> Before building hardware, we built a digital twin: the watch's real software running on a simulated body,
> live on our website.
> Here a stranger has grabbed her wrist. With her normal PIN, it simply cancels: no alert.
> On the right, she's forced to cancel, so she uses her duress PIN. The watch shows the same "Cancelled",
> but her contact's phone already has a silent alert with her location, and 112 has been called. **[Next]**

**Slide 6: Feasibility & Risk** (2:20–2:52)

> Does it work? In simulation it catches 70 % of grabs anywhere on her body and 99 % of struggles,
> with at most one false alarm in nine hours. It runs on battery, decides on the watch itself, and alerts over 4G.
> Our main risk is simple: it's simulated, not yet measured. So our next step, a battery-powered prototype,
> will measure real body voltages and real struggles. **[Next]**

**Slide 7: Impact, Business Model & Roadmap** (2:52–3:16)

> The impact: help is called even when she can't reach her phone, and her family and police get her live
> location and audio to act on.
> We'll sell the watch to individuals, offer bulk plans to colleges, hostels and employers,
> and run an alert subscription.
> For the prototype we set clear goals: 90 % of wrist grabs and 60 % anywhere. The simulation already
> beats both. **[Next]**

**Slide 8: Team** (3:16–3:22)

> We're both co-developers of SparshaGuard, guided by our faculty mentor at RV University. **[Next]**

**Slide 9: Thank you** (3:22–3:30)

> You can try the twin yourself at bhajanth13.github.io/SparshaGuard.
> SparshaGuard: the touch itself is the alarm. Thank you, we'd love your questions.

---

## Tips

- Speak slowly on slide 4: it's the part judges remember. If time is short, drop the last sentence about the papers;
  slide 4 shows it.
- On slide 5, point at the phone in each screenshot: that's where the normal and duress PINs differ.
- Likely questions: *What if a friend touches her?* The PIN cancels it. *What does it cost?* Off-the-shelf parts;
  the prototype will set the price. *Why not just an SOS app?* She doesn't have to act first.
