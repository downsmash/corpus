"""
"""

from core.stream_parser import StreamParser
from core.template_matcher import TemplateMatcher

VALID_FRAMES = [99, 98, 96, 94, 93, 91,
                89, 88, 86, 84, 83, 81,
                79, 78, 76, 74, 73, 71,
                69, 68, 66, 64, 63, 61,
                59, 58, 56, 54, 53, 51,
                49, 47, 46, 44, 42, 41,
                39, 37, 36, 34, 32, 31,
                29, 27, 26, 24, 22, 21,
                19, 17, 16, 14, 12, 11,
                9,  7,  6,  4,  2,  0]


def timer_values(start_time=480):
    """Generate the valid timer values for a single match of Melee, starting
    at `start_time` seconds and counting down.

    I haven't timed the countdown from 5 seconds to 0. Presumably it remains
    at 60 fps.
    """
    minutes, seconds = start_time // 60, int(start_time) % 60
    centis = 0
    yield "{:02d}{:02d}{:02d}".format(minutes, seconds, centis)

    for seconds_left in range(start_time - 1, 5 - 1, -1):
        minutes, seconds = seconds_left // 60, int(seconds_left) % 60

        for centis in VALID_FRAMES:
            # I believe that 00:05.00 is not shown, but have not confirmed this
            if seconds_left == 5 and centis == 0:
                return

            yield "{:02d}{:02d}{:02d}".format(minutes, seconds, centis)

class MeleeFrameSync(StreamParser):
    """
    """
    def __init__(self, filename):
        super().__init__(filename)

    def match(self, frame):

