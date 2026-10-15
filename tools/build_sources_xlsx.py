"""Build docs/SparshaGuard_parameter_sources.xlsx - every value taken from a paper, with references.

Sheets:
  Read Me            what the workbook is, legend, live counts
  Values from Papers one row per value extracted from a source (the log)
  Sources            full reference for each source ID
  Model v0.3 Params  every parameter the simulation uses, its value, tag and source IDs
  Still Estimated    values with no published source yet, and how Gate 1 should measure them

Run:  python tools/build_sources_xlsx.py
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parent.parent / "docs" / "SparshaGuard_parameter_sources.xlsx"
ACCESSED = "2026-10-11"

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3A4D")
HDR_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
BODY = Font(name=FONT, size=10)
LINK = Font(name=FONT, size=10, color="0563C1", underline="single")
TITLE = Font(name=FONT, bold=True, size=14)
BOLD = Font(name=FONT, bold=True, size=10)
THIN = Side(style="thin", color="D0D7DE")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
STATUS_FILL = {
    "In model v0.3": PatternFill("solid", fgColor="E2F0D9"),
    "Pending integration": PatternFill("solid", fgColor="FFF2CC"),
    "Benchmark only": PatternFill("solid", fgColor="DDEBF7"),
    "Context only": PatternFill("solid", fgColor="F2F2F2"),
    "Whole-body study": PatternFill("solid", fgColor="FCE4D6"),
    "Fusion study": PatternFill("solid", fgColor="EADCF0"),
    "In model (Oct 2026 update)": PatternFill("solid", fgColor="C6E0B4"),
}

# --------------------------------------------------------------------------- sources
# id, authors, title, venue, year, type, proposal ref, url, notes
SOURCES = [
    ("S1", "M. Sato, I. Poupyrev, C. Harrison",
     "Touché: Enhancing Touch Interaction on Humans, Screens, Liquids, and Everyday Objects",
     "Proc. ACM CHI 2012", 2012, "Peer-reviewed conference", "Ref 5",
     "https://la.disneyresearch.com/wp-content/uploads/touchechi20121.pdf", "Core method of the proposal"),
    ("S2", "C. Harrison, M. Sato, I. Poupyrev",
     "Capacitive Fingerprinting: Exploring User Differentiation by Sensing Electrical Properties of the Human Body",
     "Proc. ACM UIST 2012", 2012, "Peer-reviewed conference", "Ref 6",
     "https://la.disneyresearch.com/wp-content/uploads/capacitive-fingerprintingcameraready1.pdf", ""),
    ("S3", "N. Honigman et al.",
     "Techniques in Swept Frequency Capacitive Sensing: An Open Source Approach",
     "Proc. NIME 2014", 2014, "Peer-reviewed conference", "-",
     "https://nime.org/proceedings/2014/nime2014_515.pdf",
     "Arduino Touché circuit; component list also at https://github.com/sofian/touche"),
    ("S4", "N. M. Jonassen",
     "Human Body Capacitance: Static or Dynamic Concept?",
     "EOS/ESD Symposium Proceedings, pp. 111-117", 1998, "Peer-reviewed conference", "-",
     "https://backend.orbit.dtu.dk/ws/files/4363898/Jonassen.pdf", "Scanned text; some table cells hard to read"),
    ("S5", "S. Maity, M. He, M. Nath, D. Das, B. Chatterjee, S. Sen",
     "Bio-Physical Modeling, Characterization and Optimization of Electro-Quasistatic Human Body Communication",
     "IEEE Transactions on Biomedical Engineering", 2019, "Peer-reviewed journal", "-",
     "https://arxiv.org/pdf/1805.05200.pdf", "arXiv version read"),
    ("S6", "Ø. G. Martinsen, S. Grimnes, O. Sveen",
     "Dielectric properties of some keratinised tissues. Part 1: Stratum corneum and nail in situ",
     "Medical & Biological Engineering & Computing 35, 172-176", 1997, "Peer-reviewed journal", "-",
     "https://mn.uio.no/fysikk/english/research/projects/bioimpedance/publications/papers/blemme.pdf", ""),
    ("S7", "C. L. Ng, M. B. I. Reaz",
     "Characterization of Textile-Insulated Capacitive Biosensors",
     "Sensors 17(3), 574", 2017, "Peer-reviewed journal", "-",
     "https://doi.org/10.3390/s17030574", ""),
    ("S8", "S. Avlani, M. Nath, S. Maity, S. Sen",
     "A 100KHz-1GHz Termination-dependent Human Body Communication Channel Measurement using Miniaturized Wearable Devices",
     "Proc. DATE 2020, pp. 651-653", 2020, "Peer-reviewed conference", "-",
     "https://par.nsf.gov/servlets/purl/10249175", ""),
    ("S9", "(survey)",
     "Body-Area Capacitive or Electric Field Sensing for Human Activity Recognition and Human-Computer Interaction: A Comprehensive Survey",
     "arXiv:2401.06000", 2024, "Preprint (survey)", "-",
     "https://arxiv.org/abs/2401.06000", "Authors not recorded in this log"),
    ("S10", "K. Goyal, D. A. Borkholder, S. W. Day",
     "Dependence of Skin-Electrode Contact Impedance on Material and Skin Hydration",
     "Sensors 22(21), 8510", 2022, "Peer-reviewed journal", "-",
     "https://www.mdpi.com/1424-8220/22/21/8510", "PMC9656728"),
    ("S11", "A. Datta, M. Nath, D. Yang, S. Sen",
     "Advanced Biophysical Model to Capture Channel Variability for EQS Capacitive HBC",
     "arXiv:2010.15339", 2020, "Preprint", "-",
     "https://arxiv.org/pdf/2010.15339", ""),
    ("S12", "M. Nath et al. (S. Sen group, Purdue)",
     "Inter-Body Coupling in Electro-Quasistatic Human Body Communication: Theory and Analysis of Security and Interference Properties",
     "Scientific Reports", 2021, "Peer-reviewed journal", "-",
     "https://arxiv.org/pdf/2003.13329", "arXiv version read; full author list not recorded"),
    ("S13", "P. Agarwal, S. Sahu",
     "Determination of hand and palm area as a ratio of body surface area in Indian population",
     "Indian Journal of Plastic Surgery 43(1)", 2010, "Peer-reviewed journal", "-",
     "https://www.thieme-connect.de/products/ejournals/pdf/10.1055/s-0039-1699403.pdf", ""),
    ("S14", "Texas Instruments",
     "Capacitive Sensing: Ins and Outs of Active Shielding (SNOA926A)",
     "Application report", 2015, "Manufacturer app note", "-",
     "https://www.ti.com/lit/pdf/SNOA926", "Table 1 headers misaligned in source; reference column inferred"),
    ("S15", "Hackaday.io project",
     "ADC performance: Arduino vs ESP32 vs ADS1115",
     "Hackaday.io", None, "Hobby measurement (weak)", "-",
     "https://hackaday.io/project/205380-adc-performance-arduino-vs-esp32-vs-ads1115",
     "Doesn't state whether figures are std. dev. or peak-to-peak"),
    ("S16", "Espressif Systems",
     "ADC performance (developer blog)",
     "developer.espressif.com", 2025, "Manufacturer documentation", "-",
     "https://developer.espressif.com/blog/2025/08/adc-performance/", ""),
    ("S17", "Desco Industries",
     "Typical Electrostatic Voltages",
     "descoindustries.com", None, "Manufacturer reference table", "-",
     "https://www.descoindustries.com/AboutESD/Voltage.aspx", "Ranges at 10-20% vs 65-90% relative humidity"),
    ("S18", "N. Jonassen",
     "Charging by Walking (Mr. Static column)",
     "In Compliance Magazine", None, "Magazine article by researcher", "-",
     "https://incompliancemag.com/charging-by-walking/", ""),
    ("S19", "S. Bian, V. F. Rey, J. Younas, P. Lukowicz",
     "Wrist-Worn Capacitive Sensor for Activity and Physical Collaboration Recognition",
     "IEEE PerCom Workshops", 2019, "Conference paper", "-",
     "https://dfki.de/web/forschung/projekte-publikationen/publikation/10312", ""),
    ("S20", "S. Bian, M. Liu, P. Lukowicz",
     "Passive Body-Area Electrostatic Field (Human Body Capacitance) for Ubiquitous Computing",
     "arXiv:2507.13520", 2025, "Review / overview (preprint)", "-",
     "https://arxiv.org/html/2507.13520v1", ""),
    ("S21", "K. Kurita",
     "Detection method for contact electrification based on electrostatic induction",
     "Electrostatics Joint Conference", 2016, "Conference paper", "-",
     "https://electrostatics.org/wp-content/uploads/2023/08/G12.pdf", ""),
    ("S22", "H. Elfekey, H. A. Bastawrous, S. Okamoto",
     "A Touch Sensing Technique Using the Effects of Extremely Low Frequency Fields on the Human Body",
     "Sensors 16(12):2049", 2016, "Journal article", "-",
     "https://doi.org/10.3390/s16122049", ""),
    # ---- fusion study (14 Oct 2026): signals that widen coverage or confirm an attack
    ("S23", "University of Agricultural Sciences, Bangalore (GKVK agro-meteorological observatory)",
     "Monthly weather normals, GKVK, Bengaluru",
     "uasbangalore.edu.in", None, "Station climate record", "-",
     "https://uasbangalore.edu.in/images/Agrometerology/pdf/gkvk-monthly-weather-normals-2011-2020-converted.pdf",
     "Relative humidity read at 08:30 and 17:30 IST"),
    ("S24", "IPC (Electronics.org) technical resource",
     "Electrostatic Discharge (ESD), Factory Issues, Measurement Methods",
     "electronics.org", None, "Industry technical paper", "-",
     "https://www.electronics.org/system/files/technical_resource/E15&S22_02.pdf",
     "Quotes ANSI/ESD S20.20 limits for the person-footwear-floor path"),
    ("S25", "S. Bian, P. Lukowicz et al.",
     "Collaborative Human Activity Recognition with Passive Inter-Body Electrostatic Field",
     "arXiv:2501.06940", 2025, "Preprint", "-", "https://arxiv.org/pdf/2501.06940", ""),
    ("S26", "S. Bian et al.",
     "Using Human Body Capacitance Sensing to Monitor Leg Motion Dominated Activities with a Wrist Worn Device",
     "Springer (book chapter)", 2022, "Book chapter", "-",
     "https://link.springer.com/chapter/10.1007/978-981-19-0361-8_5", ""),
    ("S27", "C. E. Loeffler",
     "Detecting Gunshots Using Wearable Accelerometers",
     "PLOS ONE 9(9):e106664", 2014, "Journal article", "-",
     "https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0106664",
     "Wrist accelerometer event detection; test set included confusable activities"),
    ("S28", "P. Siirtola",
     "Continuous stress detection using the sensors of commercial smartwatch (WESAD, Empatica E4)",
     "UbiComp/ISWC adjunct", 2019, "Workshop paper", "-",
     "https://arxiv.org/pdf/2203.09669", "Wrist-only stress detection on the WESAD dataset"),
    ("S29", "P. Schmidt, A. Reiss, R. Duerichen, C. Marberger, K. Van Laerhoven",
     "Introducing WESAD, a Multimodal Dataset for Wearable Stress and Affect Detection",
     "ACM ICMI", 2018, "Conference paper", "-",
     "https://www.eti.uni-siegen.de/ubicomp/home/datasets/icmi18/", ""),
    ("S30", "(authors as listed on arXiv)",
     "Smartphone Audio Based Distress Detection",
     "arXiv:2608.04176", 2026, "Preprint", "-", "https://arxiv.org/pdf/2608.04176", ""),
    ("S31", "US Patent 10,950,112",
     "Wrist fall detector based on arm direction",
     "USPTO", None, "Patent", "-",
     "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10950112",
     "States a false-alarm budget for wrist-worn detectors"),
    ("S32", "A. Talebzadeh, M. Moradian, Y. Han, D. E. Swenson, D. Pommerenke",
     "Effect of Human Activities and Environmental Conditions on Electrostatic Charging",
     "IEEE Trans. Electromagnetic Compatibility 58(4)", 2016, "Journal article", "-",
     "https://doi.org/10.1109/TEMC.2016.2575842", "Values from the abstract"),
    ("S33", "M. Kangas, R. Korpelainen, I. Vikman, L. Nyberg, T. Jämsä",
     "Sensitivity and false alarm rate of a fall sensor in long-term fall detection in the elderly",
     "Gerontology 61(1):61-68", 2015, "Journal article", "-", "https://doi.org/10.1159/000362720", "Abstract"),
    ("S34", "F. Tchuente, N. Baddour, E. D. Lemaire",
     "Classification of Aggressive Movements Using Smartwatches",
     "Sensors 20(21):6377", 2020, "Journal article", "-", "https://doi.org/10.3390/s20216377", "Abstract; scripted movements"),
    ("S35", "Texas Instruments", "OPA350, OPA2350, OPA4350 high-speed single-supply rail-to-rail operational amplifiers (SBOS099D)",
     "Datasheet", 2015, "Datasheet", "-", "https://www.ti.com/lit/ds/symlink/opa350.pdf", "Input capacitance, typical"),
    ("S36", "ECN / passive-components.eu (using TI figures)", "A Plague of Parasites (PCB trace capacitance)",
     "Trade article", None, "Trade article", "-", "https://passive-components.eu/", "0.8 mm trace on 0.8 mm FR-4 over a plane"),
    ("S37", "Specialty Coating Systems", "Parylene Dielectric Properties", "Manufacturer technical data", None,
     "Manufacturer data", "-", "https://scscoatings.com/", "Parylene N and C relative permittivity"),
    ("S38", "A. Visuri, Z. Sarsenbayeva, N. van Berkel, J. Goncalves, R. Rawassizadeh, V. Kostakos, D. Ferreira",
     "Quantifying Sources and Types of Smartwatch Usage Sessions", "Proc. ACM CHI 2017, pp. 3569-3581", 2017,
     "Peer-reviewed conference", "-", "https://doi.org/10.1145/3025453.3025817",
     "'Half of sessions under 5 s' in the abstract; 140 sessions/day and ~9 s mean via University of Oulu news"),
    ("S39", "S. Andrews, D. A. Ellis, H. Shaw, L. Piwek",
     "Beyond Self-Report: Tools to Compare Estimated and Real-World Smartphone Use", "PLoS ONE 10(10):e0139004",
     2015, "Journal article", "-", "https://doi.org/10.1371/journal.pone.0139004",
     "85 uses/day and ~5 h/day via Lancaster University press release"),
    ("S40", "T. Ficker", "Charging by walking", "J. Phys. D: Appl. Phys. 38(5):410-417", 2005, "Journal article", "-",
     "https://incompliancemag.com/charging-by-walking/",
     "Numbers seen in In Compliance Magazine's summary of Ficker's work (secondary); check the paper"),
    ("S41", "C. Tudor-Locke, H. Han, E. J. Aguiar, et al.", "Using cadence to study free-living ambulatory activity",
     "Sports Medicine 42(5):381-398", 2012, "Journal article (review)", "-", "https://strathprints.strath.ac.uk/42646/", ""),
    ("S42", "D. Neacsu, A. Salceanu, E. Lunca, V. David", "Indirect Measurements on the Capacity in the Electrostatic HB Model",
     "IMEKO TC4 Symposium, Iasi", 2007, "Conference paper", "-",
     "https://imeko.org/proceedings/indirect-measurements-on-the-capacity-in-the-electrostatic-hb-model", "Abstract/snippet"),
    ("S43", "N. P. Dawkins, T. Yates, et al.",
     "Normative wrist-worn accelerometer values for self-paced walking and running: a walk in the park",
     "J. Sports Sciences", 2022, "Journal article", "-", "https://doi.org/10.1080/02640414.2021.1976491",
     "Averaged ENMO values, not peaks"),
    ("S44", "(authors as listed on arXiv)",
     "A 'one-size-fits-most' walking recognition method for smartphones, smartwatches, and wearable accelerometers",
     "arXiv:2207.07443", 2022, "Preprint", "-", "https://arxiv.org/abs/2207.07443", ""),
    ("S45", "(authors not visible in the abstract)",
     "Perturbation in public transport as a basic concept for perturbation-based balance training for fall prevention",
     "Z. Gerontol. Geriatr.", 2020, "Journal article", "-", "https://link.springer.com/journal/391",
     "12 days of bus and tram recordings, sensor on a vertical bar"),
    ("S46", "J. Perry, J. M. Burnfield", "Gait Analysis: Normal and Pathological Function, 2nd ed.",
     "SLACK Inc.", 2010, "Textbook", "-", "https://www.healio.com/books", "Standard gait-phase percentages"),
    ("S47", "S. Krašna, et al.",
     "Human Response to Longitudinal Perturbations of Standing Passengers on Public Transport During Regular Operation",
     "Frontiers in Bioengineering and Biotechnology 9:680883", 2021, "Journal article", "-",
     "https://doi.org/10.3389/fbioe.2021.680883", ""),
    ("S48", "Y. L. A. Kwok, J. Gralton, M.-L. McLaws", "Face touching: a frequent habit that has implications for hand hygiene",
     "American Journal of Infection Control 43(2):112-114", 2015, "Journal article", "-",
     "https://doi.org/10.1016/j.ajic.2014.10.015", ""),
    ("S49", "S. Mow, S. Seriani, T. Fujiyama",
     "Where and how often do people touch train interiors? An investigation during the pandemic",
     "Proc. ICE Municipal Engineer", 2024, "Journal article", "-", "https://discovery.ucl.ac.uk/id/eprint/10199779/", ""),
    ("S50", "Bangalore Metro Rail Corporation Ltd.", "Environmental Impact Assessment (design passenger loads)",
     "BMRCL / JICA", None, "Report", "-", "https://www.jica.go.jp/", ""),
    ("S51", "Institute for Social and Economic Change", "Determinants of intra-urban mobility: a study of Bengaluru (Working Paper 437)",
     "ISEC", 2019, "Working paper", "-", "https://ideas.repec.org/p/sch/wpaper/437.html", ""),
    ("S52", "Espressif Systems", "ESP-FAQ: ADC", "Espressif documentation", None, "Manufacturer documentation", "-",
     "https://docs.espressif.com/projects/esp-faq/", ""),
    ("S53", "(Sen group, Purdue)", "Step-to-Charge (EQS body powering)", "arXiv:2408.01927", 2024, "Preprint", "-",
     "https://arxiv.org/abs/2408.01927", ""),
    ("S54", "IEC", "IEC 61000-4-2: Electrostatic discharge immunity test", "International standard", 2008, "Standard", "-",
     "https://webstore.iec.ch/publication/4189", "Human-body model and current waveform"),
    ("S55", "(Al-Quds / An-Najah University)", "Residential exposure to ELF electric and magnetic fields in the city of Ramallah-Palestine",
     "Journal article", None, "Journal article", "-", "https://dspace.alquds.edu/items/bc4377ca-bfb7-4375-ab1a-435c8e020c57/full", ""),
    ("S56", "O. Aziz, et al.", "Validation of accuracy of SVM-based fall detection system using real-world fall and non-fall datasets",
     "PLoS ONE 12(7):e0180318", 2017, "Journal article", "-", "https://doi.org/10.1371/journal.pone.0180318", ""),
    ("S57", "M. Indraganti, et al.", "Thermal insulation of Indian clothing ensembles (sari, salwar-kurti)",
     "Windsor Conference", 2014, "Conference paper", "-", "https://architexturez.net/node/175314", ""),
    ("S58", "B. B. Majumdar, et al. (BITS Pilani Hyderabad)", "Harassment of women in public transport, Hyderabad",
     "Transportation Research Record", None, "Journal article", "-", "https://journals.sagepub.com/home/trr",
     "Numbers via press coverage (secondary)"),
    ("S59", "K. Nabors, J. White",
     "FastCap: A Multipole Accelerated 3-D Capacitance Extraction Program",
     "IEEE Trans. Computer-Aided Design 10(11):1447-1459", 1991, "Journal article", "-",
     "https://doi.org/10.1109/43.97624", "Reference solver used to check the 3D field calculation"),
    ("S60", "H. Vogt, G. Atkinson, P. Nenzi", "Ngspice User's Manual", "ngspice project", None, "Manual", "-",
     "https://ngspice.sourceforge.io/docs.html", "Circuit simulator used to check the Python solver"),
]

SHORT = {"S1": "Sato et al. 2012 (Touché)", "S2": "Harrison et al. 2012 (Cap. Fingerprinting)",
         "S3": "Honigman et al. 2014 (Arduino Touché)", "S4": "Jonassen 1998", "S5": "Maity et al. 2019",
         "S6": "Martinsen et al. 1997", "S7": "Ng & Reaz 2017", "S8": "Avlani et al. 2020",
         "S9": "Capacitive sensing survey 2024", "S10": "Goyal et al. 2022", "S11": "Datta et al. 2020",
         "S12": "Nath et al. 2021", "S13": "Agarwal & Sahu 2010", "S14": "TI SNOA926 2015",
         "S15": "Hackaday ADC test", "S16": "Espressif ADC blog 2025",
         "S17": "Desco ESD table", "S18": "Jonassen (walking)", "S19": "Bian et al. 2019",
         "S20": "Bian, Liu, Lukowicz 2025", "S21": "Kurita 2016", "S22": "Elfekey et al. 2016",
         "S23": "GKVK Bengaluru weather normals", "S24": "IPC ESD resource (ANSI/ESD S20.20)",
         "S25": "Bian et al. 2025 (collaborative)", "S26": "Bian et al. 2022 (leg motion)",
         "S27": "Loeffler 2014", "S28": "Siirtola 2019", "S29": "Schmidt et al. 2018 (WESAD)",
         "S30": "Audio distress detection 2026", "S31": "US Pat. 10,950,112",
         "S32": "Talebzadeh et al. 2016", "S33": "Kangas et al. 2015", "S34": "Tchuente et al. 2020",
         "S35": "TI OPA350 datasheet", "S36": "ECN trace capacitance", "S37": "SCS parylene data",
         "S38": "Visuri et al. 2017", "S39": "Andrews et al. 2015", "S40": "Ficker 2005",
         "S41": "Tudor-Locke et al. 2012", "S42": "Neacsu et al. 2007", "S43": "Dawkins et al. 2022",
         "S44": "Walking recognition 2022", "S45": "Public transport perturbation 2020",
         "S46": "Perry & Burnfield 2010", "S47": "Krašna et al. 2021", "S48": "Kwok et al. 2015",
         "S49": "Mow et al. 2024", "S50": "BMRCL EIA", "S51": "ISEC WP 437 (2019)", "S52": "Espressif ESP-FAQ",
         "S53": "Step-to-Charge 2024", "S54": "IEC 61000-4-2", "S55": "Ramallah ELF survey",
         "S56": "Aziz et al. 2017", "S57": "Indraganti et al. 2014", "S58": "Majumdar et al. (Hyderabad)",
         "S59": "Nabors & White 1991 (FastCap)", "S60": "ngspice manual"}

# --------------------------------------------------------------------------- values
# category, parameter, value, unit, conditions, source, location, status, used-as, notes
IN, PEND, BENCH, CTX = "In model v0.3", "Pending integration", "Benchmark only", "Context only"
WB = "Whole-body study"
FU = "Fusion study"
UP = "In model (Oct 2026 update)"
V = [
    # ---- S1 Touché
    ("Sweep", "Sweep range", "1 kHz – 3.5 MHz", "Hz", "Swept sine, AD5932 generator", "S1", "Hardware section", IN, "Sweep grid 1 kHz – 3.4835 MHz", ""),
    ("Sweep", "Frequency step", 17.5, "kHz", "", "S1", "Hardware section", IN, "17.5 kHz", ""),
    ("Sweep", "Steps per sweep", 200, "count", "", "S1", "Hardware section", IN, "200", ""),
    ("Sweep", "Excitation amplitude", 6.6, "V p-p", "After amplification", "S1", "Hardware section", CTX, "Results in % of full scale; cancels out", ""),
    ("Sweep", "Sweep duration", 33, "ms", "~33 Hz update; ~100 Hz if only high band swept", "S1", "Hardware section", IN, "Basis of 5 frames/s pipeline", ""),
    ("Circuit", "Bias inductor Lb", "~100", "mH", "Tunes sensitivity at lower frequencies", "S1", "Hardware section", CTX, "Model uses Arduino version 10 mH (S3)", ""),
    ("Measurement", "Measured quantity", "Amplitude only", "-", "Envelope detector; phase not measured", "S1", "Hardware section", IN, "Amplitude-only score and classifier", ""),
    ("Measurement", "ADC resolution", 12, "bit", "Max 200 kHz sampling", "S1", "Hardware section", IN, "Basis of noise estimate", ""),
    ("Device", "Sensor board size / mass", "36 × 36 × 5.5 mm, 13.8 g", "-", "", "S1", "Hardware section", CTX, "", ""),
    ("Body", "Trunk internal resistance", "~100", "Ω", "Average", "S1", "Body-as-sensor section", IN, "+100 Ω added to limb resistance", ""),
    ("Skin", "Dry intact skin resistance", "~1", "MΩ", "", "S1", "Body-as-sensor section", IN, "Dry end of hydration range", "Contact area not stated"),
    ("Classifier", "Classifier", "SVM (Weka SMO), polynomial kernel, C = 2.0", "-", "Features: 200 raw + derivatives + minima", "S1", "Classification section", IN, "SVM (RBF) and random forest", ""),
    ("Accuracy", "On-body (wrist-to-wrist), 5 gestures, per user", 84.0, "%", "SD 11.4%", "S1", "Study 4", BENCH, "", "Closest to a wrist-worn sensor"),
    ("Accuracy", "On-body, 5 gestures, walk-up", 52.9, "%", "SD 13.8%; no per-user training", "S1", "Study 4", BENCH, "", ""),
    ("Accuracy", "On-body, 3 gestures, walk-up", 87.1, "%", "SD 12.5%", "S1", "Study 4", BENCH, "", ""),
    ("Accuracy", "Mobile mockup (ungrounded), 5 gestures", 93.3, "%", "SD 6.2%; walk-up 76.1%", "S1", "Study 3", BENCH, "", "Authors call it the hardest setup"),
    ("Accuracy", "Doorknob (grounded), 5 gestures", 96.7, "%", "SD 5.6%", "S1", "Study 1", BENCH, "", ""),
    ("Accuracy", "Table (body configuration), 7 gestures", 92.6, "%", "SD 9.4%", "S1", "Study 2", BENCH, "", ""),
    ("Accuracy", "Liquid (fish tank), 5 gestures", 99.8, "%", "SD 0.8%", "S1", "Study 5", BENCH, "", "Source of the '99%' headline"),
    ("Accuracy", "Participants", 12, "people", "9 male, 3 female (studies 1-4)", "S1", "Studies", BENCH, "", ""),
    # ---- S2 Capacitive Fingerprinting
    ("Sweep", "Sweep range / steps", "1 kHz – 3.5 MHz, 200 steps", "-", "", "S2", "Implementation", IN, "Same as S1", ""),
    ("Safety", "Current through body", "< 0.5", "mA", "6.6 V p-p sine", "S2", "Implementation", CTX, "", "Described as safe"),
    ("Accuracy", "User differentiation, 8 s training", 97.3, "%", "SD 5.9%; 11 people, 55 pairings", "S2", "Results", BENCH, "", ""),
    ("Accuracy", "User differentiation, 0.1 s training", 84.5, "%", "SD 18.9%", "S2", "Results", BENCH, "", ""),
    ("Accuracy", "Best single frequency (753.5 kHz)", 87.3, "%", "vs 97.3% for full sweep", "S2", "Results", BENCH, "Supports using the full sweep", ""),
    ("Body", "Bone resistivity", "45 → 90", "Ω·m", "1 kHz → 1 MHz (cited from their ref 11)", "S2", "Background", CTX, "", ""),
    ("Drift", "Calibration drift over a day", "Qualitative", "-", "Temperature, humidity, hydration; re-login needed after hours", "S2", "Discussion", IN, "Adaptive baseline in pipeline", "No numbers given"),
    # ---- S3 Honigman (Arduino Touché)
    ("Circuit", "Series resistor R1", 10, "kΩ", "Arduino SFCS circuit, Fig. 2", "S3", "Fig. 2", IN, "Rs = 10 kΩ", ""),
    ("Circuit", "Inductor L1", 10, "mH", "", "S3", "Fig. 2", IN, "L = 10 mH ±5%", ""),
    ("Circuit", "Tank capacitor C2", 100, "pF", "Listed as 0.1 nF", "S3", "Fig. 2", IN, "Ctank = 100 pF ±5%", ""),
    ("Circuit", "Envelope detector", "1N4148, 10 nF, 1 MΩ, 3.3 kΩ", "-", "", "S3", "Fig. 2", CTX, "", ""),
    ("Sweep", "Max frequencies per sweep (Arduino library)", 198, "count", "", "S3", "Text", CTX, "", ""),
    # ---- S4 Jonassen
    ("Body", "Body capacitance: polymer shoes, linoleum", "160–170", "pF", "AC bridge, 1 kHz", "S4", "Table 1", IN, "Street shoes 110–170 pF", ""),
    ("Body", "Body capacitance: polymer shoes, asphalt", 110, "pF", "AC bridge", "S4", "Table 1", IN, "Street shoes 110–170 pF", ""),
    ("Body", "Body capacitance: leather shoes, asphalt", 115, "pF", "AC bridge", "S4", "Table 2", IN, "Street shoes 110–170 pF", ""),
    ("Body", "Body capacitance: barefoot, linoleum", 250, "pF", "AC bridge", "S4", "Table 1", IN, "Barefoot 185–250 pF", ""),
    ("Body", "Body capacitance: barefoot, asphalt", 185, "pF", "AC bridge", "S4", "Table 1", IN, "Barefoot 185–250 pF", ""),
    ("Body", "Body capacitance: on plastic over metal", "900–2850", "pF", "AC bridge; condition partly illegible", "S4", "Table 2", CTX, "", ""),
    ("Body", "Body capacitance, charge-sharing method", "200–400", "pF", "50–200% above AC values", "S4", "Abstract", CTX, "AC values used (closer to kHz–MHz)", ""),
    ("Body", "Calculated body-to-walls (cylinder)", 40, "pF", "h 1.7 m, r 0.2 m, walls 2 m", "S4", "Calculation", CTX, "", ""),
    ("Body", "Calculated feet-to-floor", "70–260", "pF", "Soles 200–300 cm², 5–10 mm, εr 4–5", "S4", "Calculation", CTX, "", "Feet dominate body capacitance"),
    ("Body", "Standard human-body model", 100, "pF", "ESD standard", "S4", "Text", CTX, "", ""),
    ("Body", "Frequency dependence 100 Hz–10 kHz", "None detected", "-", "", "S4", "Text", CTX, "", ""),
    # ---- S5 Maity
    ("Body", "Body-to-ground capacitance (measured)", 150, "pF", "Total, split 75 + 75 pF in model", "S5", "Table I / text", IN, "Cross-check for C_BE", ""),
    ("Body", "Tissue resistance", "200 (100–400)", "Ω", "Subcutaneous", "S5", "Table I", IN, "Limb 100–400 Ω", ""),
    ("Skin", "Skin resistance", "10 k (1 k–100 k)", "Ω", "4 cm²; depends on moisture", "S5", "Table I", CTX, "Superseded by S6/S10 per-area values", ""),
    ("Skin", "Skin capacitance", 90, "pF", "4 cm², 4 mm, εr ~100", "S5", "Table I", CTX, "", ""),
    ("Device", "Band-to-skin capacitance", "200 (354 calc.)", "pF", "4 cm² electrode, 0.01 mm", "S5", "Table I", CTX, "", ""),
    ("Body", "Feet-to-ground capacitance", 9, "pF", "100 cm² feet at 1 cm", "S5", "Table I", CTX, "", ""),
    ("Device", "Device ground plane to body", 0.3, "pF", "4 cm² ground plane at 1 cm (354 fF calc.)", "S5", "Table I", CTX, "Watch uses own geometry (closer, larger)", ""),
    ("Device", "Return-path capacitance of a wearable", 1.5, "pF", "Experimentally estimated", "S5", "Table I / text", IN, "1.0–2.0 pF single; 1.5–3.0 pF dual", "S11 suggests lower at the wrist"),
    ("Device", "Wearable input load capacitance", 1, "pF", "10 MΩ", "S5", "Table I", CTX, "", ""),
    ("Measurement", "Channel loss, wearable prototype", "−49 to −52", "dB", "Forearm Tx to wrist Rx, 20–25 cm", "S5", "Results", CTX, "", ""),
    # ---- S6 Martinsen
    ("Skin", "Stratum corneum DC conductance", 4.4, "µS/cm²", "In situ, palm, hydrogel electrodes", "S6", "Fig. 1 circuit", IN, "G_DC per cm²", ""),
    ("Skin", "Polarisation conductance G0", 100, "nS/cm²", "G = G0·f^m", "S6", "Fig. 1 circuit", IN, "", ""),
    ("Skin", "Polarisation capacitance C0", 50, "nF/cm²", "C = C0·f^(m−1)", "S6", "Fig. 1 circuit", IN, "", ""),
    ("Skin", "CPE exponent m", 0.8, "-", "Phase angle ≈ 72°", "S6", "Text", IN, "0.75–0.85", ""),
    ("Skin", "R∞", "< 1", "kΩ", "", "S6", "Text", CTX, "", ""),
    # ---- S7 Ng & Reaz
    ("Clothing", "Cotton", "εr 3.004; 0.23 mm; Cs 58.96 pF", "-", "1 kHz; electrode 510 mm²", "S7", "Table", IN, "εr 1.2–5.1; 0.16–0.58 mm", ""),
    ("Clothing", "Linen", "εr 4.007; 0.40 mm; Cs 45.22 pF", "-", "1 kHz; 510 mm²", "S7", "Table", IN, "", ""),
    ("Clothing", "Rayon", "εr 5.082; 0.58 mm; Cs 39.56 pF", "-", "1 kHz; 510 mm²", "S7", "Table", IN, "", ""),
    ("Clothing", "Nylon", "εr 1.222; 0.48 mm; Cs 11.49 pF", "-", "1 kHz; 510 mm²", "S7", "Table", IN, "", ""),
    ("Clothing", "Polyester", "εr 1.178; 0.16 mm; Cs 33.24 pF", "-", "1 kHz; 510 mm²", "S7", "Table", IN, "", ""),
    ("Clothing", "PVC-textile", "εr 3.118; 0.24 mm; Cs 58.65 pF", "-", "1 kHz; 510 mm²", "S7", "Table", CTX, "", ""),
    # ---- S8 Avlani
    ("Circuit", "Buffer input capacitance", 2.1, "pF", "1 MΩ input", "S8", "Setup", IN, "Sense-node parasitics 2–7 pF", ""),
    ("Device", "Return path vs device size", "Proportional to ground-plane size (≈ self-capacitance)", "-", "", "S8", "Text", IN, "Self-capacitance check 8·ε₀·r", ""),
    # ---- S9 survey
    ("Body", "Typical body capacitance", "~100", "pF", "Several cited studies", "S9", "Section 3.2", CTX, "", ""),
    ("Drift", "Main source of body-capacitance variation", "Feet actions", "-", "Qualitative", "S9", "Section 3.2.1", IN, "Walking drift on C_BE", ""),
    # ---- S10 Goyal (pending)
    ("Skin", "|Z| at 10 Hz, stainless steel, in vivo", 2.68, "MΩ·cm²", "Thigh, 10 people, dry electrode", "S10", "Results", IN, "Confirms phantom fit values used", "Matches watch back plate"),
    ("Skin", "|Z| at 10 Hz, titanium, in vivo", 2.06, "MΩ·cm²", "Thigh, dry electrode", "S10", "Results", CTX, "", ""),
    ("Skin", "Stratum corneum resistance Rsc, dry", 6.4, "MΩ·cm²", "Phantom fit", "S10", "Table 2", IN, "Rsc at hyd = 0", ""),
    ("Skin", "Stratum corneum resistance Rsc, hydrated", 3.0, "MΩ·cm²", "Phantom fit", "S10", "Table 2", IN, "Rsc at hyd = 1", ""),
    ("Skin", "Stratum corneum capacitance Csc, dry", 41, "nF/cm²", "Phantom fit", "S10", "Table 2", IN, "Csc at hyd = 0", ""),
    ("Skin", "Stratum corneum capacitance Csc, hydrated", 190, "nF/cm²", "Phantom fit", "S10", "Table 2", IN, "Csc at hyd = 1", ""),
    ("Skin", "Contact capacitance Cc, titanium / steel (dry)", "267 / 114", "nF/cm²", "Phantom fit", "S10", "Table 2", IN, "Steel 114 nF/cm²; Ti ratio for hydrated", "Titanium gives better contact"),
    ("Skin", "CPE exponents", "α ≈ 0.9 (SC); β ≈ 0.5–0.6 (contact)", "-", "", "S10", "Results", IN, "α 0.88–0.92; β 0.5–0.6", ""),
    ("Skin", "Hydration effect on impedance", "~10× lower when hydrated", "-", "", "S10", "Results", IN, "Hydration 0..1 range", ""),
    ("Skin", "Frequency range measured", "0.1 Hz – 100 kHz", "Hz", "", "S10", "Methods", CTX, "", "Below most of our sweep"),
    # ---- S11 Datta (pending)
    ("Device", "Return-path factor x at the wrist", 0.3642, "-", "Fraction of free-space self-capacitance", "S11", "Fig. 8 table", IN, "C_GE = 8ε₀a × 0.364 ≈ 0.45 pF (low end)", "Highest of the measured locations"),
    ("Device", "Return-path factor x at the elbow", 0.2139, "-", "", "S11", "Fig. 8 table", CTX, "", ""),
    ("Device", "Return-path factor x at the shoulder", 0.0588, "-", "", "S11", "Fig. 8 table", CTX, "", ""),
    ("Device", "Return-path factor x at the torso", 0.1457, "-", "", "S11", "Fig. 8 table", CTX, "", ""),
    ("Device", "Free-space return path of a small device", "≈ 1", "pF", "Device radius a few cm; C = 8·ε₀·a", "S11", "Section III-A", IN, "8ε₀a self-capacitance", ""),
    ("Device", "Receiver return path", "< 1", "pF", "", "S11", "Section IV-A", CTX, "", ""),
    ("Body", "Tissue / skin resistance (order)", "~100 Ω / ~10 kΩ", "-", "", "S11", "Section III-A", CTX, "", ""),
    # ---- S12 Nath inter-body (pending)
    ("Bystander", "Body-to-body capacitance at 1 m", 21, "pF", "Electrostatic FEM", "S12", "Fig. 7(a) / text", IN, "Bystander 21–40 pF", "Model now uses 2–15 pF at 0.2–0.5 m: too low"),
    ("Bystander", "Body-to-body capacitance at 5 m", 6.6, "pF", "Electrostatic FEM", "S12", "Text", CTX, "", ""),
    ("Body", "Body-to-ground capacitance", 150, "pF", "Fixed in model", "S12", "Text", CTX, "Agrees with S4/S5", ""),
    # ---- S13 Agarwal (pending)
    ("Anatomy", "Hand area (palmar, incl. fingers), men", "146.5 ± 15.1", "cm²", "Indian adults 18–60, n = 150", "S13", "Results", IN, "Grab contact 40–80 cm² = 30–55% of hand", "Supports 40–80 cm² grab contact"),
    ("Anatomy", "Hand area (palmar, incl. fingers), women", "132.4 ± 14.1", "cm²", "n = 150", "S13", "Results", IN, "Grab contact 40–80 cm²", ""),
    ("Anatomy", "Palm area, men", "77.9 ± 10.3", "cm²", "", "S13", "Results", CTX, "", ""),
    ("Anatomy", "Palm area, women", "73.7 ± 9.1", "cm²", "", "S13", "Results", CTX, "", ""),
    ("Anatomy", "Hand as % of body surface area", "0.92", "%", "Men and women", "S13", "Results", CTX, "", ""),
    # ---- S14 TI (pending)
    ("Shield", "Unshielded ground parasitic", "> 100 (can be)", "pF", "", "S14", "Fig. 4", CTX, "", ""),
    ("Shield", "Rejection of object behind sensor (3.6 cm)", "50.9 / 61.1 / 76.3", "% reduction", "Same-size shield / 200% shield / ring + shield", "S14", "Table 1", IN, "Shield residual 20–50%", "Residual 24–49%"),
    ("Shield", "Rejection of object at side (1 cm)", "37.2 / 70.6 / 77.0", "% reduction", "Same three configurations", "S14", "Table 1", IN, "Shield residual 20–50%", "Residual 23–63%"),
    ("Shield", "Rejection of object at side (5 cm)", "34.2 / 64.6 / 75.0", "% reduction", "Same three configurations", "S14", "Table 1", CTX, "", ""),
    ("Shield", "Loss of wanted sensitivity (top, 1 cm)", "23.6 / 26.5 / 39.3", "% reduction", "Same three configurations", "S14", "Table 1", CTX, "", "Shield also costs some signal"),
    # ---- S15/S16 ADC (pending)
    ("Measurement", "ESP32 built-in ADC fluctuation", "~21.8", "mV", "Unclear if std. dev. or p-p; ≈27 LSB at 3.3 V", "S15", "Results", IN, "Noise 0.1% of full scale after averaging", "Weak source"),
    ("Measurement", "Arduino ADC fluctuation", "~4.2", "mV", "", "S15", "Results", CTX, "", ""),
    ("Measurement", "ADS1115 fluctuation", "~2", "mV", "", "S15", "Results", CTX, "", "External ADC option"),
    ("Measurement", "ESP32 calibrated error", "< 30", "mV", "", "S16", "Results", CTX, "", "Accuracy, not noise"),
    ("Measurement", "ESP32-S3 calibrated error", "−30 to 0", "mV", "", "S16", "Results", CTX, "", ""),
    ("Measurement", "ESP32 / ESP32-S3 DNL, INL", "±7, ±12 / ±4, ±8", "LSB", "Datasheet values", "S16", "Table 1", CTX, "", ""),
    ("Measurement", "ESP32 ADC sample rate", "200 k (RTC) / 2 M (DIG)", "samples/s", "", "S16", "Table 1", CTX, "", ""),
    ("Measurement", "Noise advice", "100 nF on ADC input; multisampling", "-", "No figures given", "S16", "Text", CTX, "", ""),
    # ---- S17-S22 whole-body detection study (docs/whole_body_detection.md)
    ("Static charge", "Body voltage, walking on vinyl floor", "250 – 12,000", "V", "65-90% / 10-20% relative humidity", "S17", "Table", WB, "Fig 11 shaded band", ""),
    ("Static charge", "Body voltage, walking on carpet", "1,500 – 35,000", "V", "65-90% / 10-20% relative humidity", "S17", "Table", WB, "", ""),
    ("Static charge", "Body voltage from walking on vinyl (measured)", "up to ~3,500", "V", "Insulating floor", "S18", "Text", WB, "Her own steps: artefact size", ""),
    ("Passive sensing", "Wrist passive field sensor sensitivity", "microvolt-level", "-", "Wrist-worn, passive", "S19", "Text", WB, "Supports passive channel", "Qualitative"),
    ("Passive sensing", "ProxiBand: approaching person detected (TPR)", "74.3 / 46", "%", "Indoor / outdoor", "S20", "Overview text", WB, "Supports passive channel", ""),
    ("Passive sensing", "Contact moment from electrostatic induction current", "detected", "-", "Contact electrification", "S21", "Results", WB, "Supports charge-sharing step", "Qualitative"),
    ("Passive sensing", "Touch sensing from induced 50 Hz field on body", "demonstrated", "-", "Mains ELF field", "S22", "Results", WB, "50 Hz hum cue", "Qualitative"),
    # ---- fusion study (14 Oct 2026)
    ("Static charge", "Peak walking voltage formula", "V_max = R · n · Δq", "-", "R to ground, n steps per second, Δq charge per step", "S18", "Text", FU, "Charge-sharing step size", ""),
    ("Static charge", "Body resistance to ground from initial decay", "≈ 2 × 10^10", "Ω", "Walking test, decay after stopping", "S18", "Text", FU, "Decay τ = R·C ≈ 3 s with 150 pF", ""),
    ("Static charge", "Person-footwear-floor path limit in ESD areas", "< 1.0 × 10^9", "Ω", "ANSI/ESD S20.20", "S24", "Text", CTX, "ESD shoes drain charge in < 0.2 s", "Ordinary shoes are far above this"),
    ("Static charge", "ESD footwear resistance, low end", "≈ 5 × 10^5", "Ω", "Commercial ESD footwear", "S24", "Text", CTX, "", ""),
    ("Bystander", "Body-to-body capacitance at 1 m (analytic)", 20, "pF", "Two 1.8 m people", "S12", "Text", FU, "Cross-check of FEM 21 pF", ""),
    ("Passive sensing", "Hum at the controller input, touching vs not touching", "> 4 / < 0.5", "V", "Their sensing circuit, indoor mains field", "S22", "Results", FU, "Hum changes with contact: person vs earthed object cue", "Circuit-specific levels"),
    ("Climate", "Relative humidity at 08:30, Bengaluru", "85 – 89", "%", "Monthly means, GKVK station", "S23", "Table", FU, "Humid case", ""),
    ("Climate", "Relative humidity at 17:30, Bengaluru", "37 – 58", "%", "Monthly means (37 % Mar–Apr, 57–58 % Jul–Aug)", "S23", "Table", FU, "Dry and typical cases", ""),
    ("Climate", "Annual mean relative humidity at 17:30, Bengaluru", 50, "%", "GKVK station", "S23", "Table", FU, "Typical case", ""),
    ("Passive sensing", "Wrist body-capacitance vs IMU, leg-motion activities (F-score)", "0.89 vs 0.78", "-", "Wrist-worn, leg-dominated activities", "S26", "Results", BENCH, "", ""),
    ("Passive sensing", "Gain from adding body capacitance to wrist accelerometer (collaborative activities)", "+16", "% F-score", "Collaborative activity recognition", "S25", "Results", BENCH, "", ""),
    ("Motion", "Wrist accelerometer event detection accuracy (gunshot recoil)", 99.4, "%", "Hold-out set incl. confusable activities", "S27", "Results", BENCH, "Wrist IMU can separate sharp events", "Lab conditions"),
    ("Physiology", "Wrist-only stress detection, balanced accuracy", 87.4, "%", "Empatica E4, WESAD, LDA", "S28", "Results", BENCH, "", ""),
    ("Physiology", "Stress vs non-stress accuracy (best, chest device)", 93, "%", "WESAD", "S29", "Abstract", BENCH, "", "Chest, not wrist"),
    ("Audio", "Scream stage false alarm rate, before / after context filter", "≈ 10 / ≈ 1", "%", "Smartphone, daily audio", "S30", "Results", BENCH, "", "1 % ≈ 15 min of false alarms per day"),
    ("Motion", "Acceptable false-alarm budget for wrist detectors", "≈ 1", "per user per day", "Stated as technically reasonable; many users find it too many", "S31", "Background", BENCH, "Target for fused alerts", "Patent text"),
    # ---- 14 Oct 2026: values found for the remaining estimates
    ("Static charge", "Body voltage, worst case (incl. walking)", "> ±20", "kV", "22 °C, 5 % RH", "S32", "Abstract", CTX, "Upper end of the body-voltage sweep", ""),
    ("Static charge", "Body capacitance to ground on concrete vs wood-frame floor", "120 vs 60", "pF", "Same person; concrete gives about half the voltage", "S32", "Abstract", CTX, "Floors change voltage ~2x", ""),
    ("Static charge", "Spread of body voltage from capacitance differences alone", "±30", "%", "", "S32", "Abstract", CTX, "", ""),
    ("Static charge", "Time for body charge to fall to 100 V without ESD shoes/floor", "1 – 30", "min", "With ESD shoes/floor: 0.5–6 s", "S32", "Abstract", UP, "Supports R up to 1e11 Ω (τ up to ~25 s)", ""),
    ("Static charge", "Body capacitance standing on both feet / on one foot", "160 / 100", "pF", "Vinyl tile", "S40", "Summary article", UP, "C_B × 0.625 in single support", "Secondary"),
    ("Static charge", "Body resistance to ground on vinyl tile", "≈ 10^11", "Ω", "", "S40", "Summary article", UP, "Upper end of R range", "Secondary"),
    ("Static charge", "Lifting a foot raises body voltage", "8 – 12", "×", "Walking on resistive floors", "S40", "Summary", CTX, "", "Secondary"),
    ("Static charge", "Change of body capacitance, sitting on a wooden chair vs standing", "< 10", "pF", "", "S42", "Abstract", UP, "Her own movement changes C_B by 2–7 %", ""),
    ("Static charge", "Measured human body capacitance, range", "50 – 500", "pF", "", "S42", "Abstract", CTX, "", ""),
    ("Static charge", "Body capacitance barefoot on 1 rubber carpet / on 4 carpets", "295 / 116", "pF", "", "S42", "Snippet", CTX, "", ""),
    ("Static charge", "Human-body model (test standard)", "150 pF, 330 Ω", "-", "Discharge time constant ≈ 50 ns; rise time 0.8 ns ±25 %", "S54", "Standard", UP, "Charge sharing at contact settles far inside one 2 ms sample", ""),
    ("Gait", "Walking cadence, women (normal lab walking)", "96 – 138", "steps/min", "Across the lifespan", "S41", "Abstract", UP, "1.6–2.3 steps/s", ""),
    ("Gait", "Gait phases: double support / loading response / toe-off", "0–10 % and 50–60 % / 0–10 % / 60 %", "% of stride", "Normal walking", "S46", "Textbook", UP, "Timing of C_B changes per step", ""),
    ("Motion", "Wrist acceleration (ENMO), slow / normal / brisk walking", "140 / 210 / 350", "mg", "Adults 40–69, wrist, averaged", "S43", "Abstract", UP, "Arm-swing amplitude π × ENMO", "Averaged, not peaks"),
    ("Motion", "Walking periodicity; wrist shows half the step rate", "≈ 1.7", "Hz", "Pooled datasets", "S44", "Snippet", UP, "Arm swing at half the cadence", ""),
    ("Motion", "Bus acceleration from standstill / braking into a stop, maxima", "3.37 / −3.12", "m/s²", "12 days, sensor on a vertical bar", "S45", "Abstract", UP, "Bus jolts 0.1–0.34 g", ""),
    ("Motion", "Tram acceleration / braking maxima", "1.80 / −2.31", "m/s²", "Same study", "S45", "Abstract", CTX, "", ""),
    ("Motion", "Standing-passenger perturbation pulses tested", "1.5 and 3.0 (acc.), 1.0 and 2.5 (braking)", "m/s²", "Sled tests, 24 volunteers", "S47", "Abstract", CTX, "", ""),
    ("Motion", "Aggressive-movement classification, smartwatch", "99.6 % accuracy, 98.4 % sensitivity", "-", "30 people, scripted punch/shove/slap", "S34", "Abstract", BENCH, "", "Scripted"),
    ("Motion", "Fall-sensor false alarms in long-term use", "0.049 (0.025 improved)", "per hour", "16 older adults, 15,500 h", "S33", "Abstract", BENCH, "Benchmark for unwanted prompts", ""),
    ("Motion", "Fall-detector false alarms, real-world", "0 – 0.3", "per hour", "≈ 400 h, waist/sternum", "S56", "Abstract", BENCH, "", ""),
    ("Daily life", "Smartwatch usage sessions", "≈ 140", "per day", "307 users; about two-thirds are glances", "S38", "Abstract + news", UP, "≈ 47 touch interactions/day ≈ 3 per hour", "140/day secondary"),
    ("Daily life", "Smartwatch sessions shorter than 5 s; mean session", "half; ≈ 9 s", "-", "", "S38", "Abstract + news", UP, "Log-normal, median 5 s, mean 9 s", ""),
    ("Daily life", "Smartphone uses per day; total use", "≈ 85; ≈ 5 h", "-", "23 adults, 2 weeks; more than half under 30 s", "S39", "Press release", UP, "5.3 per hour, median 30 s, mean 212 s", "Secondary"),
    ("Daily life", "Face touching", 23, "per hour", "26 students in a lecture", "S48", "Abstract", CTX, "Wrist self-touch not found", ""),
    ("Daily life", "Train-interior touches per passenger movement", "0.07 – 0.57", "touches", "London Underground, 16,891 passengers", "S49", "Abstract", CTX, "", ""),
    ("Daily life", "Bengaluru Metro design loads (standing)", "4 / 6 / 8", "per m²", "Normal / crush / dense crush", "S50", "Report", CTX, "", ""),
    ("Daily life", "One-way commute in Bengaluru", 42.45, "min", "10.84 km average", "S51", "Abstract", CTX, "Bus/metro hours per day", ""),
    ("Circuit", "OPA350 input capacitance", "≈ 9", "pF", "Typical", "S35", "Datasheet", UP, "Sense-node parasitics 2.1–9 pF", ""),
    ("Circuit", "PCB trace capacitance", 0.8, "pF/cm", "0.8 mm trace on 0.8 mm FR-4 over a plane", "S36", "Article", UP, "0.6–0.8 pF/cm × 1–3 cm", ""),
    ("Circuit", "ESP32 SAR ADC sample-and-hold capacitance", "≈ 1", "pF", "", "S52", "FAQ", CTX, "", ""),
    ("Circuit", "Parylene relative permittivity, N / C", "2.65 / 2.95–3.15", "-", "1 MHz (C: 3.15 at 60 Hz)", "S37", "Data sheet", UP, "Coating εr 2.65–3.15", ""),
    ("Return path", "Wearable floating ground to earth", "≤ 1", "pF", "Wearable form factors", "S53", "Abstract", CTX, "Consistent with C_GE 0.4–2 pF", ""),
    ("Passive sensing", "Indoor 50 Hz electric field in homes, geometric mean", 9.6, "V/m", "32 homes, log-normal", "S55", "Abstract", CTX, "", ""),
    ("Clothing", "Thermal insulation of a sari, by drape", "0.62 – 0.94", "clo", "Manikin, ISO 9920", "S57", "Abstract", CTX, "", ""),
    ("Harassment", "Physical harassment in public transport: touching / groping", "58.8 / 53.2", "% of victims", "Hyderabad, 583 respondents", "S58", "Press", CTX, "", "Secondary"),
]

# --------------------------------------------------------------------------- model params
# parameter, symbol, value used (v0.2), unit, tag, sources, note
P = [
    ("Sweep grid", "FREQS", "1 kHz + 17.5 kHz·k, k = 0..199", "Hz", "S", "S1, S2", ""),
    ("Series resistor", "Rs", "10", "kΩ", "S", "S3", ""),
    ("Inductor", "L", "10 ±5%", "mH", "S", "S3", ""),
    ("Tank capacitor + node parasitics", "Ctank", "100 ±5% + 2.1–9 + (0.6–0.8 pF/cm × 1–3 cm)", "pF", "S/D", "S3, S8, S35, S36", "Trace length is a design choice"),
    ("Measurement noise", "NOISE", "0.1", "% of full scale", "S/E", "S15", "Weak source; measure on the board"),
    ("Inner electrode area", "el_area", "2–4", "cm²", "D", "-", "Design choice, stainless steel"),
    ("Stratum corneum R and C", "z_sc", "Rsc 6.4→3.0 MΩ·cm², Csc 41→190 nF/cm², α 0.88–0.92", "per cm²", "S", "S10", "Dry → hydrated"),
    ("Metal contact", "z_metal", "114 nF/cm² (×1.57 hydrated), β 0.5–0.6", "per cm²", "S", "S10", ""),
    ("Skin hydration", "hyd", "0 (dry) – 1 (hydrated)", "-", "S", "S10", ""),
    ("Wrist-to-trunk tissue", "Rbody", "100–400 + 100", "Ω", "S", "S5, S1", ""),
    ("Watch ground to wrist (PCB)", "C_GB", "3–13", "pF", "G", "-", "8–12 cm², 2–4 mm, εr 1.5–2.5"),
    ("Outer strap electrode to wrist", "C_GB (dual)", "+15–60", "pF", "G", "-", "20–30 cm², 1.5–3 mm, εr 2.5–3.5"),
    ("Driven-shield residual", "-", "20–50", "%", "S", "S14", ""),
    ("Body to surroundings, street shoes", "C_BE", "110–170", "pF", "S", "S4, S5", ""),
    ("Body to surroundings, barefoot", "C_BE", "185–250", "pF", "S", "S4", ""),
    ("Body to surroundings, sandals", "C_BE", "130–210", "pF", "E", "-", "Interpolated"),
    ("Body to surroundings, car seat", "C_BE", "150–300", "pF", "E", "-", ""),
    ("Walking change in C_BE", "-", "160 → 100 pF (σ 0.235)", "-", "S", "S4, S40", "Sweep insensitive (≤ 0.002 % FS)"),
    ("Watch return path, single electrode", "C_GE", "0.4–1.5", "pF", "S/G", "S11, S5", "8ε₀a × 0.364 to Maity's 1.5 pF"),
    ("Watch return path, with outer electrode", "C_GE", "0.6–2.0", "pF", "G/E", "S11", "Upper end estimated"),
    ("Car body factor on return path", "-", "×1.3–2", "×", "E", "-", ""),
    ("Second person to surroundings", "C_AE", "110–170 (+40–130 in car)", "pF", "S/E", "S4", ""),
    ("Hand contact area (grab)", "area", "40–80", "cm²", "S", "S13", "30–55% of hand area"),
    ("Clothing permittivity", "er", "1.2–5.1", "-", "S", "S7", ""),
    ("Clothing thickness", "t", "0.16–0.58 per layer, 1–2 layers", "mm", "S/E", "S7", ""),
    ("Outer-electrode coating", "coat", "25–100 µm, εr 2.65–3.15", "-", "D/S", "S37", "Thickness is a design choice; parylene εr"),
    ("His palm on outer electrode", "Z_A0", "skin 10–20 cm² + coating", "-", "E", "S10", "Palm area on strap estimated"),
    ("His hand near strap (forearm)", "Z_A0", "0.5–3", "pF", "E", "-", ""),
    ("His body 0.3–0.6 m from watch", "Z_A0", "2–20% of return path", "-", "E", "-", ""),
    ("Bystander body-to-body", "Z_BA", "21–40", "pF", "S/E", "S12", "21 pF at 1 m; closer is higher"),
    ("Own hand: both arms", "r_arms", "2 × 100–400", "Ω", "S", "S5", ""),
    ("Railing grip area", "-", "20–40", "cm²", "E", "S13", "Bounded by hand area"),
    ("Strap on metal pole", "-", "coating over 2–10 cm²", "-", "G", "-", ""),
    ("Phone self-capacitance", "-", "4–12", "pF", "G/E", "-", "8·ε₀·r, r 6–10 cm"),
    ("Wooden table, bag", "-", "1–20", "pF", "E", "-", ""),
    ("Strap-gap jitter", "-", "1.5 (normal) / 5 (strong)", "%", "E", "-", ""),
]

STILL_E = [
    ("Watch return path on our board (C_GE)", "0.4–1.5 pF (single)", "S11 ~0.45 pF at the wrist; S5 ~1.5 pF", "Battery board on wrist: inject a known signal and compare with a reference capacitor (method in S5/S11)", 1),
    ("His palm on the outer electrode", "Skin 10–20 cm² + coating", "No direct source", "Sweep change for firm grab vs light touch on the strap", 2),
    ("Shield residual on our layout", "20–50%", "S14: 23–66% for flat shields", "Measure watch-to-wrist coupling with the shield driven vs grounded", 3),
    ("Measurement noise on our board", "0.1% of full scale", "S15 weak source", "Log 1,000 sweeps with nothing touching; compute std. dev. per point", 4),
    ("Strap-gap jitter while walking", "1.5–5%", "No source", "Log sweeps for 10 minutes of walking and arm movement", 5),
    ("His hand a few cm from the strap", "0.5–3 pF", "No source", "Forearm-grab trials at 2, 5, 10 cm from the strap", 6),
    ("Body capacitance in sandals / car seat", "130–210 / 150–300 pF", "No measurement found", "Measure with an LCR meter at 1–100 kHz (Jonassen's method)", 7),
    ("Wrist on wooden table; bag", "1–20 pF", "No source", "Record sweeps during these events", 8),
]


# --------------------------------------------------------------------------- helpers
def header(ws, row, cols, widths):
    for i, (name, w) in enumerate(zip(cols, widths), start=1):
        c = ws.cell(row=row, column=i, value=name)
        c.font, c.fill, c.border = HDR_FONT, HDR_FILL, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 30


def body_cell(c, wrap=True):
    c.font, c.border = BODY, BORDER
    c.alignment = Alignment(wrap_text=wrap, vertical="top")


def main():
    wb = Workbook()

    # ---------------- Values from Papers
    ws = wb.active
    ws.title = "Values from Papers"
    cols = ["ID", "Category", "Parameter", "Value", "Unit", "Conditions / context", "Source ID",
            "Source (short)", "Location in source", "Status", "How it's used in the model", "Notes"]
    widths = [7, 12, 34, 22, 11, 32, 9, 26, 16, 18, 30, 30]
    ws.cell(row=1, column=1, value="Values from papers").font = TITLE
    ws.cell(row=2, column=1, value="One row per value taken from a source. Status colours: green = in model v0.2, "
            "yellow = found, awaiting integration, blue = accuracy benchmark, grey = context only.").font = BODY
    header(ws, 4, cols, widths)
    for i, (cat, par, val, unit, cond, src, loc, status, used, note) in enumerate(V, start=1):
        r = 4 + i
        vals = [f"V{i:03d}", cat, par, val, unit, cond, src, None, loc, status, used, note]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            body_cell(c)
        # short source name looked up from the Sources sheet
        ws.cell(row=r, column=8, value=f'=IFERROR(INDEX(Sources!$B:$B,MATCH(G{r},Sources!$A:$A,0)),"")')
        body_cell(ws.cell(row=r, column=8))
        ws.cell(row=r, column=10).fill = STATUS_FILL[status]
        if isinstance(val, (int, float)):
            ws.cell(row=r, column=4).alignment = Alignment(horizontal="left", vertical="top")
    last_v = 4 + len(V)
    ws.freeze_panes = "D5"
    ws.auto_filter.ref = f"A4:L{last_v}"
    dv = DataValidation(type="list", formula1='"In model v0.3,Pending integration,Benchmark only,Context only"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"J5:J{last_v + 200}")

    # ---------------- Sources
    ss = wb.create_sheet("Sources")
    cols = ["Source ID", "Short name", "Authors", "Title", "Venue", "Year", "Type", "Proposal ref", "Link",
            "Accessed", "Notes", "Values logged"]
    widths = [9, 30, 30, 52, 30, 7, 20, 10, 40, 11, 34, 9]
    ss.cell(row=1, column=1, value="Sources").font = TITLE
    ss.cell(row=2, column=1, value="Full reference for every source ID used in this workbook and in sg_model.py.").font = BODY
    header(ss, 3, cols, widths)
    for i, s in enumerate(SOURCES, start=1):
        r = 3 + i
        sid, auth, title, venue, year, typ, pref, url, note = s
        vals = [sid, SHORT[sid], auth, title, venue, year if year else "n.d.", typ, pref, url, ACCESSED, note, None]
        for j, v in enumerate(vals, start=1):
            c = ss.cell(row=r, column=j, value=v)
            body_cell(c)
        lc = ss.cell(row=r, column=9)
        lc.hyperlink, lc.font = url, LINK
        ss.cell(row=r, column=12, value=f"=COUNTIF('Values from Papers'!$G:$G,A{r})")
        body_cell(ss.cell(row=r, column=12))
    ss.freeze_panes = "B4"
    ss.auto_filter.ref = f"A3:L{3 + len(SOURCES)}"

    # ---------------- Model v0.3 Params
    ms = wb.create_sheet("Model v0.3 Params")
    cols = ["Parameter", "Symbol in sg_model.py", "Value used", "Unit", "Tag", "Source IDs", "Note"]
    widths = [36, 18, 34, 14, 7, 14, 40]
    ms.cell(row=1, column=1, value="Parameters used by simulation v0.3").font = TITLE
    ms.cell(row=2, column=1, value="Tag: S = published source, G = geometry calculation, D = our design choice, "
            "E = estimate (no source yet).").font = BODY
    header(ms, 3, cols, widths)
    tag_fill = {"S": "E2F0D9", "G": "DDEBF7", "D": "EDE7F6", "E": "FCE4D6"}
    for i, row in enumerate(P, start=1):
        r = 3 + i
        for j, v in enumerate(row, start=1):
            body_cell(ms.cell(row=r, column=j, value=v))
        t = row[4].split("/")[-1]
        ms.cell(row=r, column=5).fill = PatternFill("solid", fgColor=tag_fill.get(t, "FFFFFF"))
    ms.freeze_panes = "B4"
    ms.auto_filter.ref = f"A3:G{3 + len(P)}"

    # ---------------- Still Estimated
    es = wb.create_sheet("Still Estimated")
    cols = ["Parameter", "Current value (v0.3)", "What the literature says", "How Gate 1 should measure it", "Priority"]
    widths = [36, 22, 40, 52, 9]
    es.cell(row=1, column=1, value="Values still estimated — measure these in Gate 1").font = TITLE
    es.cell(row=2, column=1, value="Priority 1 matters most for the results.").font = BODY
    header(es, 3, cols, widths)
    for i, row in enumerate(STILL_E, start=1):
        for j, v in enumerate(row, start=1):
            body_cell(es.cell(row=3 + i, column=j, value=v))
    es.freeze_panes = "B4"

    # ---------------- Read Me (first sheet)
    rm = wb.create_sheet("Read Me", 0)
    rm.column_dimensions["A"].width = 34
    rm.column_dimensions["B"].width = 70
    rm["A1"] = "SparshaGuard — parameter sources"
    rm["A1"].font = TITLE
    rows = [
        ("Purpose", "Every value taken from a paper for the SparshaGuard simulation, with its full reference, "
                    "and every parameter the model uses with where it came from."),
        ("Project folder", "D:\\SPARSHA  (model: sg_model.py; notes: docs\\parameter_sources.md, docs\\new_findings_pending.md)"),
        ("Last updated", ACCESSED),
        ("", ""),
        ("Sheets", ""),
        ("Values from Papers", "The log: one row per value, with source, location in the source and status."),
        ("Sources", "Full reference and link for each source ID."),
        ("Model v0.3 Params", "Each parameter in sg_model.py, the value used, and its tag and sources."),
        ("Still Estimated", "Values with no published source yet, and how Gate 1 should measure them."),
        ("", ""),
        ("Adding a value", "Add a row at the bottom of 'Values from Papers'. Fill Category to Location, pick a "
                           "Status from the drop-down, and use a Source ID listed on 'Sources' "
                           "(add the source there first if it's new). The short source name fills in by itself."),
        ("", ""),
        ("Counts (live)", ""),
    ]
    r = 2
    for a, b in rows:
        r += 1
        rm.cell(row=r, column=1, value=a).font = BOLD if a and not b.startswith("D:") else BODY
        c = rm.cell(row=r, column=2, value=b)
        c.font, c.alignment = BODY, Alignment(wrap_text=True, vertical="top")
    counts = [
        ("Sources", "=COUNTA(Sources!$A$4:$A$500)"),
        ("Values logged", "=COUNTA('Values from Papers'!$A$5:$A$1000)"),
        ("In model v0.3", "=COUNTIF('Values from Papers'!$J:$J,\"In model v0.3\")"),
        ("Pending integration", "=COUNTIF('Values from Papers'!$J:$J,\"Pending integration\")"),
        ("Benchmark only", "=COUNTIF('Values from Papers'!$J:$J,\"Benchmark only\")"),
        ("Context only", "=COUNTIF('Values from Papers'!$J:$J,\"Context only\")"),
        ("Model parameters", "=COUNTA('Model v0.3 Params'!$A$4:$A$500)"),
        ("…of which still estimated (tag E)", "=COUNTIF('Model v0.3 Params'!$E$4:$E$500,\"E\")"),
    ]
    for a, f in counts:
        r += 1
        rm.cell(row=r, column=1, value=a).font = BODY
        c = rm.cell(row=r, column=2, value=f)
        c.font, c.alignment = BODY, Alignment(horizontal="left")
    for row in rm.iter_rows(min_row=3, max_row=r):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print("wrote", OUT, len(V), "values,", len(SOURCES), "sources,", len(P), "params")


if __name__ == "__main__":
    main()
