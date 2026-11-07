# SparshaGuard explainer: narration script

## 0:00  Title

The word Sparsha means touch. This is SparshaGuard: a smartwatch for women's safety that notices when someone else touches her. First you'll see how she uses it, and then exactly how it works inside.

## 0:13  The idea: the touch itself raises the alarm

Most safety apps need her to act. She has to find the phone, unlock it, open the app and press SOS. During an attack, there may be no time for any of that. But SparshaGuard flips the default. Once it's armed, another person's touch starts the alert by itself. She only has to act if she wants to cancel it.

## 0:33  Step 1 · She turns on Guard Mode

Step one. When she's walking alone at night, sitting in a cab or an auto, or standing in a crowded bus, she turns on Guard Mode. From then on, the watch keeps checking, many times every second, what is touching the skin around it.

## 0:48  Step 2 · Someone grabs her wrist

Step two. A stranger grabs her wrist. The watch doesn't react to every brush. It waits about two seconds, to be sure the touch is real and still there. Then it vibrates and asks for her PIN. She has fifteen seconds to answer.

## 1:07  Step 3 · What happens next

Step three. There are three possible outcomes. If she enters the correct PIN, the alert is cancelled. That's how a friend's hug or a handshake is handled: the PIN takes care of friendly contact. If she enters nothing, or a wrong PIN, the fifteen seconds run out. The watch then sends an SMS with her GPS location to her trusted contacts, calls 112, and starts recording audio. The third option is the duress PIN. If the attacker forces her to cancel, she enters this special PIN. The screen shows 'Cancelled', but the alert goes out silently.

## 1:43  Other ways it raises the alarm

There are other ways the alarm can start. If the watch is pulled off in Guard Mode, it alerts at once, so an attacker can't simply remove it. A motion sensor detects struggling, being dragged, or a fall. A microphone listens for a scream or a call for help. It does this on the watch itself, and only in Guard Mode. And a proposed next step: detecting a touch anywhere on her body, not just near the watch. Part two explains how.

## 2:11  The whole user flow

So here's the whole flow for her. She arms Guard Mode. A touch is detected. The watch checks that it lasts about two seconds, then gives her fifteen seconds for the PIN. After that, it cancels, raises the alert, or fakes a cancel while alerting silently. That's everything the user needs to know.

## 2:29  Inside the watch

Part two: how it works. Inside the watch, a small signal generator chip, the AD9833, produces a sine wave. The wave goes through a coil-and-capacitor circuit called the tank, and into her skin through a metal electrode. A detector measures how big the wave is at the electrode, and an analog-to-digital converter turns that into numbers. Whatever touches her changes that size. The ESP32 microcontroller is the brain. It reads the numbers, decides what's happening, runs the PIN, and sends alerts over 4G with GPS. It also reads the motion sensor and the microphone.

## 3:09  Physics 1 · Capacitance, and why shoes don't stop it

To understand the sensing, start with capacitance. Two conductors separated by an insulator form a capacitor. Its value is C equals epsilon A over d. Bigger plates, or a thinner gap, give more capacitance. Now, her body is a conductor. The floor, the walls, and everything around her act as the other plate. Measurements by Jonassen show a person has roughly 110 to 250 picofarads to their surroundings, depending on footwear. Shoes are just the gap d in the formula. They change the capacitance a little, but they don't block it. That's why the watch still works when she wears shoes.

## 3:49  Physics 2 · A capacitor is a 'wall' for small C

For an alternating signal, a capacitor behaves like a resistance that depends on frequency. That's its impedance: Z equals one over two pi f C. At 100 kilohertz, her body's 140 picofarads to the room is only about 11 kilo-ohms. That's an easy path. But one picofarad is about 1.6 mega-ohms. That's almost a wall. Remember this: the watch runs on a battery, and its own link to the room is only about one picofarad. That tiny wall shapes the whole design.

## 4:23  Physics 3 · The resonant tank

The drive circuit is the open-source Arduino Touché tank: a 10 kilo-ohm resistor, a 10 millihenry coil, and a 100 picofarad capacitor. Together they resonate: the voltage at the sense point, S, peaks near one frequency. The natural frequency is one over two pi root L C, which is about 156 kilohertz. The resistor damps it, so the actual peak sits near 108 kilohertz. When the electrode touches her wrist, her body adds capacitance, and the peak moves down to about 90 kilohertz. This loaded curve is the watch's normal state: the baseline.

## 5:01  Physics 4 · Swept-frequency sensing (Touché)

Instead of measuring at one frequency, the watch sweeps through 200 of them, from 1 kilohertz to about 3.5 megahertz, in steps of 17.5 kilohertz. At each step it records the amplitude. Those 200 numbers form a fingerprint of whatever is touching the watch. This method is called swept-frequency capacitive sensing, from the Touché paper by Sato and colleagues. When he grabs her wrist, the peak collapses. Near 90 kilohertz, the amplitude falls from about 1.1 to about 0.3. That change is the signal we detect.

## 5:38  The model · Five nodes and one tiny link

To simulate all this, the situation is modelled as a circuit with five nodes. S is the sense node, B is her body, A is the other person, E is the earth and surroundings, and zero is the watch's own ground. Her body couples strongly to the room, about 140 picofarads, and so does his. But the watch runs on a battery, so its ground floats. It is joined to the room by only about half a picofarad to two picofarads. This link is called C G E. This is the bottleneck. When he grabs her wrist with his palm on the watch's outer electrode, he creates a short, strong path from his body straight to the watch ground. That path skips the bottleneck, which is why wrist grabs are easy to see.

## 6:23  Why a far touch is nearly invisible

Here are the simulated results with the recommended design. A wrist grab changes the sweep by about 16 percent of full scale. A forearm grab changes it by about a quarter of a percent. A shoulder grab changes it by only about 0.02 percent, which is below the measurement noise of about 0.1 percent. The reason is that a far touch only changes her body's coupling to the room. The watch sees that change through the one picofarad bottleneck, so only about one part in 150 reaches the sensor.

## 6:58  Design fix · Two electrodes and a driven shield

This is why the design uses two electrodes. The inner electrode is stainless steel, touching the skin under the watch. The outer electrode is a coated mesh over the case and strap, connected to the watch ground. When his palm lands on the outer electrode, his whole body, with its 140 picofarads to the room, connects directly to the watch ground. That raises the wrist-grab signal from a quarter of a percent to about 13 percent. A driven shield sits between the electrodes and the circuit board. It cancels part of the unwanted coupling between the strap and her wrist. Texas Instruments measured 50 to 75 percent. With the shield, a wrist grab gives about 16 percent.

## 7:42  Physics 5 · Skin is not a wire

Skin isn't a simple wire. Its outer layer, the stratum corneum, behaves like a resistor in parallel with a leaky capacitor, called a constant phase element. Sweat changes it a lot. From dry to sweaty, the resistance drops from about 6.4 to 3 mega-ohm square centimetres, and the capacitance rises from 41 to 190 nanofarads per square centimetre. These values come from Goyal and colleagues, 2022. So the baseline drifts as she sweats. The software has to keep re-learning what normal looks like, and react only to sudden changes.

## 8:20  Software 1 · From 200 numbers to a decision

Now the software. Each new sweep is compared with a slowly adapting baseline. The score is the root-mean-square change across all 200 points, as a percentage of full scale. The ESP32's converter adds about 0.1 percent of noise. So a touch must cross a trigger level of 0.3 percent to count. While a touch is happening, the baseline freezes, so the touch isn't learned as normal. There's also hysteresis: the score must rise above a high level to start, and fall below a lower level to end, so the decision doesn't flicker. If the score stays high for two seconds, the PIN prompt starts.

## 9:00  Software 2 · Who touched it? The classifier

The score says that something changed. The shape of the change says what it was. There are four classes: no contact, an object, her own hand, or another person. A metal railing looks different from a hand. Her own hand differs from his only in small details of the curve. The features are the 200 amplitude changes, compressed with an inverse hyperbolic sine, so that both small and large changes count. Two models were tested: a support vector machine and a random forest, trained on 18,000 simulated events. In simulation, the random forest gets 75 percent across all four classes, and 92 percent on the key question: is a hand at the watch? Her own hand is sorted correctly about 94 percent of the time. For comparison, the original Touché paper reported 84 percent for on-body gestures.

## 9:53  The simulation · What the numbers say today

Every value in the model comes from published measurements: 113 values from 22 sources, all listed in the project's Excel sheet. A Monte Carlo simulation draws thousands of random combinations of skin, footwear, clothing and hardware within those published ranges. Running the full pipeline over simulated hours of daily life, it catches about 93 percent of wrist grabs, and 43 percent of forearm grabs. It produces about 5.5 unwanted PIN prompts per hour, mostly from the strap pressing on a metal pole, her own hand on the watch, or her wrist on a table. One warning for testing: if the watch is powered from a laptop over USB, its ground is connected to earth. That removes the bottleneck, and a far grab looks about twenty times bigger than it really will. So real tests must run on battery.

## 10:47  Next step · A touch anywhere on her body

Can the watch detect a touch anywhere on her body? With the current method, no circuit improvement can fix this. Even with a near-ideal front end, a shoulder grab gives 0.47 percent, and simply walking past a wall gives 0.41 percent, because both act through the same one picofarad link. So here's a new idea. People carry static charge, so two bodies usually sit at different voltages. Just walking can charge a person to hundreds, or even thousands, of volts. When he touches her anywhere, the two bodies share charge in a fraction of a millisecond. Her whole body's voltage jumps by about half the difference between them, and the floating watch sees a fixed fraction of that jump. That's about 30 millivolts per volt of difference with the current design, or about 150 with a better amplifier. An ADS1115 converter, with about 2 millivolts of noise, could see a difference of 0.1 to 0.5 volts. The catch: her own footsteps make bigger jumps, so the accelerometer must filter them out. This idea still needs real measurements.

## 11:56  Putting it together · Sensor fusion

Putting it all together, four channels feed one decision on the ESP32. The active sweep sees a hand at the wrist, and whose it is. The passive channel catches the moment of contact anywhere. The motion sensor detects struggle and falls, and recognises her own steps. The microphone listens for distress. Any strong reason starts the PIN prompt. Because the PIN handles friendly contact, the system can afford to be sensitive.

## 12:24  If a judge asks…

Finally, short answers for the judges. Does it work with shoes? Yes. Capacitive coupling passes through insulation. Shoes only change her body capacitance, and the result barely changes. Why not the AD7746 chip from the proposal? It measures at one fixed frequency, over a few picofarads. We need a frequency sweep, and a body of about 100 picofarads. How do you avoid false alarms? A two-second rule, an adaptive baseline, hysteresis, a classifier, and the PIN for friendly contact. And we measure unwanted prompts per hour, not just accuracy. Is it tested on hardware? Not yet. It's a simulation built from published values. The next stage, Gate 1, is a battery-powered prototype that will calibrate the model with real measurements.

## 13:14  Close

That is SparshaGuard: touch, check, PIN, help. Thank you.
