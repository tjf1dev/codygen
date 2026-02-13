from typing import Any
import matplotlib.pyplot as plt
import numpy as np


# --- base converter ---
class LevelConverterBase:
    """base class for all level converters"""

    def __init__(self, xp: int | None = None, level: int | None = None) -> None:
        self._xp = xp
        self._level = level

    @property
    def level(self) -> float | None:
        raise NotImplementedError

    @property
    def xp(self) -> float | None:
        raise NotImplementedError

    def chart(self, max_level: int = 100):
        levels = np.arange(1, max_level + 1)
        total_xp = np.array([self.__class__(level=int(level)).xp for level in levels])

        plt.figure(figsize=(10, 6))
        plt.plot(levels, total_xp)
        plt.xlabel("level")
        plt.ylabel("total xp required")
        plt.title(
            f"xp required to reach levels 1-{max_level} ({self.__class__.__name__})"
        )
        plt.grid(True)
        plt.savefig("chart.png", dpi=150)


# --- v2 converter ---
def _old_xp_to_level(xp: int) -> int:
    level = 1
    xp_needed = 100
    increment = 50
    while xp >= xp_needed:
        xp -= xp_needed
        level += 1
        xp_needed += increment
    return level


class LevelConverterV2(LevelConverterBase):
    @property
    def level(self) -> int | None:
        if self._xp is None:
            return None
        return _old_xp_to_level(self._xp)

    @property
    def xp(self) -> int | None:
        if self._level is None:
            return None
        total_xp = 0
        xp_needed = 100
        increment = 50
        for lvl in range(1, self._level):
            total_xp += xp_needed
            xp_needed += increment
        return total_xp


# --- v3 converter (current) ---
def adjusted_xp_cost(level: int, base_xp: float = 50, exponent: float = 1.24) -> float:
    return base_xp * (level**exponent)


def level_to_xp(level: int, base_xp: float = 50, exponent: float = 1.24) -> int:
    return round(
        sum(adjusted_xp_cost(lvl, base_xp, exponent) for lvl in range(1, level + 1))
    )


def xp_to_level(xp: int | float, base_xp: float = 50, exponent: float = 1.24) -> int:
    level = 1
    while True:
        cost = adjusted_xp_cost(level, base_xp, exponent)
        if xp < cost:
            break
        xp -= cost
        level += 1
    return level


class LevelConverterV3(LevelConverterBase):
    def __init__(
        self,
        xp: int | None = None,
        level: int | None = None,
        base_xp: float = 50,
        exponent: float = 1.24,
    ):
        super().__init__(xp, level)
        self.base_xp = base_xp
        self.exponent = exponent

    @property
    def level(self) -> int:
        if self._xp is None:
            raise ValueError(".level property required xp to be set")
        return xp_to_level(self._xp, self.base_xp, self.exponent)

    @property
    def xp(self) -> int:
        if self._level is None:
            raise ValueError(".xp property requires level to be set")

        return level_to_xp(self._level, self.base_xp, self.exponent)


converter = LevelConverterV3
