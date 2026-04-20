# -- Global Chart Configuration --
# Centralises all visual design tokens (colours, fonts, sizes) and applies
# them as a matplotlib rcParams theme. Ensures visual consistency across
# all generated analysis charts through a single configuration surface.

import matplotlib.pyplot as plt
from cycler import cycler

class ChartConfig:

    # -- Canvas Dimensions --
    FIGURE_WIDTH: float = 19.20
    FIGURE_HEIGHT: float = 10.80
    DPI: int = 100
    OUTPUT_FORMAT: str = "png"

    # -- Dark Theme Colour Palette --
    BG_COLOR: str = "#0F1117"
    PANEL_COLOR: str = "#1A1D2E"
    TEXT_COLOR: str = "#E8E8EC"
    GRID_COLOR: str = "#2A2D3E"
    ACCENT_COLORS: list[str] = [
        "#6C5CE7",  # Purple
        "#00B894",  # Mint
        "#FD79A8",  # Pink
        "#FDCB6E",  # Yellow
        "#74B9FF",  # Blue
        "#E17055",  # Orange
        "#A29BFE",  # Lavender
        "#55EFC4",  # Teal
        "#FF7675",  # Coral
        "#81ECEC",  # Cyan
        "#FAB1A0",  # Peach
        "#DDA0DD",  # Plum
    ]

    # -- Category-Specific Colour Assignments --
    CATEGORY_COLORS: dict[str, str] = {
        "Kulaklık": "#6C5CE7",
        "Mouse": "#00B894",
        "Klavye": "#FD79A8",
    }

    # -- Semantic Colour Tokens --
    POSITIVE_COLOR: str = "#00B894"
    NEGATIVE_COLOR: str = "#FF7675"
    NEUTRAL_COLOR: str = "#74B9FF"

    # -- Typography --
    FONT_FAMILY: str = "Segoe UI"
    TITLE_SIZE: int = 20
    SUBTITLE_SIZE: int = 14
    LABEL_SIZE: int = 13
    TICK_SIZE: int = 11
    LEGEND_SIZE: int = 12
    ANNOTATION_SIZE: int = 10

    @classmethod
    def apply_theme(cls) -> None:
        # Inject all design tokens into matplotlib's global rcParams
        plt.rcParams.update({
            # Figure defaults
            "figure.figsize": (cls.FIGURE_WIDTH, cls.FIGURE_HEIGHT),
            "figure.dpi": cls.DPI,
            "figure.facecolor": cls.BG_COLOR,
            "figure.edgecolor": cls.BG_COLOR,

            # Axes styling
            "axes.facecolor": cls.PANEL_COLOR,
            "axes.edgecolor": cls.GRID_COLOR,
            "axes.labelcolor": cls.TEXT_COLOR,
            "axes.titlecolor": cls.TEXT_COLOR,
            "axes.titlesize": cls.TITLE_SIZE,
            "axes.labelsize": cls.LABEL_SIZE,
            "axes.grid": True,
            "axes.prop_cycle": cycler(color=cls.ACCENT_COLORS),

            # Grid lines
            "grid.color": cls.GRID_COLOR,
            "grid.linewidth": 0.5,
            "grid.alpha": 0.6,

            # Tick marks
            "xtick.color": cls.TEXT_COLOR,
            "ytick.color": cls.TEXT_COLOR,
            "xtick.labelsize": cls.TICK_SIZE,
            "ytick.labelsize": cls.TICK_SIZE,

            # Typography
            "text.color": cls.TEXT_COLOR,
            "font.family": cls.FONT_FAMILY,
            "font.size": cls.LABEL_SIZE,

            # Legend
            "legend.facecolor": cls.PANEL_COLOR,
            "legend.edgecolor": cls.GRID_COLOR,
            "legend.fontsize": cls.LEGEND_SIZE,
            "legend.labelcolor": cls.TEXT_COLOR,

            # Export defaults
            "savefig.facecolor": cls.BG_COLOR,
            "savefig.edgecolor": cls.BG_COLOR,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.3,
        })

    @classmethod
    def get_figsize(cls) -> tuple[float, float]:
        # Convenience accessor for the standard figure dimensions
        return (cls.FIGURE_WIDTH, cls.FIGURE_HEIGHT)
