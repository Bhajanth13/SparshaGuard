"""Shared figure style (light theme, presentation-friendly)."""
import matplotlib as mpl
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GOOD, WARN, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"

DESIGN_LABEL = {"single": "Single electrode",
                "dual": "Inner + outer electrode",
                "dual_shield": "Inner + outer + driven shield"}
DESIGN_COLOR = {"single": SERIES[0], "dual": SERIES[1], "dual_shield": SERIES[2]}
LOC_LABEL = {"wrist": "Wrist (watch arm)", "forearm": "Forearm (watch arm)",
             "upper_arm": "Upper arm (watch arm)", "other_arm": "Other arm",
             "shoulder": "Shoulder", "waist": "Waist", "face_hair": "Face / hair"}
ENV_LABEL = {"street_shoes": "Street shoes", "sandals": "Sandals",
             "barefoot_tile": "Barefoot on tiles", "car_seat": "Seated in a car"}


def apply():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "legend.frameon": False, "legend.fontsize": 9.5,
        "lines.linewidth": 2.0, "lines.solid_capstyle": "round",
    })


def subtitle(ax, text):
    ax.text(0, 1.015, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=9.5, color=INK2)


def footnote(fig, text):
    fig.text(0.01, 0.005, text, ha="left", va="bottom", fontsize=8, color=MUTED)


def save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
