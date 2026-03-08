"""Representative transcript examples for parser behavior."""

from __future__ import annotations

from .parser import parse_transcript
from .schemas import ParsedOutput


EXAMPLE_INPUTS: list[str] = [
    "take result from calculator 1, add 2, convert liters to mL, write to journal",
    "write down result 5.2 milliliters",
    "look up protocol for PCR cleanup",
    "sample 4 became cloudy after heating",
    "take the previous value and write it down",
    "convert 5 liters to milliliters",
    "calculate sinus of 30 degrees",
    "hello how are you",
]


def get_example_outputs() -> list[ParsedOutput]:
    """Parse all example inputs and return structured outputs."""
    return [parse_transcript(text) for text in EXAMPLE_INPUTS]


print(get_example_outputs())
