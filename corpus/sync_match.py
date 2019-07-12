"""
"""

from pkg_resources import resource_string

import numpy as np
import cv2

from core.stream_parser import StreamParser
from core.template_matcher import TemplateMatcher
from core.rect import Rect


VALID_FRAMES = [99, 98, 96, 94, 93, 91,
                89, 88, 86, 84, 83, 81,
                79, 78, 76, 74, 73, 71,
                69, 68, 66, 64, 63, 61,
                59, 58, 56, 54, 53, 51,
                49, 47, 46, 44, 42, 41,
                39, 37, 36, 34, 32, 31,
                29, 27, 26, 24, 22, 21,
                19, 17, 16, 14, 12, 11,
                9, 7, 6, 4, 2, 0]


def is_valid(time):
    """Return whether the given string represents a frame that can occur
    on Melee's timer.

    Parameters
    ----------
    time : str
        A string.
    """
    return (len(time) == 6 and time.isnumeric()
            and int(time[4:]) in VALID_FRAMES)


def distance(fr, to):
    """Return the number of frames after the valid timestamp `fr` at which
    the valid timestamp `to` will appear.

    Parameters
    ----------
    fr : str
        A six-digit string representing a valid timestamp. (This would have
        been named "from" if it weren't a Python reserved word.)
    to : str
        A six-digit string representing a valid timestamp.

    Returns
    -------
    int
        The directed distance, in frames, from `fr` to `to`. Positive if `fr`
        is the higher of the two.
    """

    if not (is_valid(fr) and is_valid(to)):
        return None

    minutes = int(to[:2]) - int(fr[:2])
    seconds = int(to[2:4]) - int(fr[2:4])
    frames = VALID_FRAMES.index(int(to[4:])) - VALID_FRAMES.index(int(fr[4:]))

    # We subtract `frames` because the array of valid frames is in reverse.
    return (minutes * 60 * 60) + (seconds * 60) - frames


def get_digit_image(digit, small=False, color=False, white=False):
    """Return the asset corresponding to the requested timer `digit`, as it
    would appear in-game.

    Parameters
    ----------
    digit : int
        The digit (from 0 to 9) whose texture is to be returned.

    small
        Whether to return the texture scaled to the "small" size used for
        centiseconds. (The default is the "large" size used for minutes and
        seconds.)

    color
        Whether to return the texture in color. (The default is black and
        white.)

    white
        Whether to return the texture on a white background. (The default is
        black.)


    Returns
    -------
    img : ndarray
        The image of the appropriate digit as an OpenCV-compatible array.
    """

    if digit not in range(10):
        return None

    if white:
        path = resource_string("times", "{0}_time_white.png".format(digit))
    else:
        path = resource_string("times", "{0}_time_black.png".format(digit))

    nparr = np.frombuffer(path, np.uint8)
    img = cv2.imdecode(nparr, 1)

    if not color:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # The assets as used in-game are very slightly wider than the textures.
    img = cv2.resize(img, (0, 0), fx=39/37, fy=1)

    if small:
        img = cv2.resize(img, (0, 0), fx=21/24, fy=21/24)
    else:
        img = cv2.resize(img, (0, 0), fx=26/24, fy=26/24)

    return img


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
            # I believe that 00:05.00 is not shown,
            # but have not confirmed this
            if seconds_left == 5 and centis == 0:
                return

            yield "{:02d}{:02d}{:02d}".format(minutes, seconds, centis)


class MeleeFrameSync(StreamParser):
    """
    """
    @staticmethod
    def match_digit(scene, small=False):
        """Given a masked frame, estimate the uncovered digit.
        """
        matcher = TemplateMatcher(worst_match=0.45)

        conf_array = [0 for n in range(10)]

        for n in range(10):
            digit = get_digit_image(n, small=small)
            _, candidates = matcher.match(digit, scene, scale=1)
            if candidates:
                _, conf_black = max(candidates, key=lambda k: k[1])
            else:
                conf_black = 0

            digit = get_digit_image(n, white=True, small=small)
            _, candidates = matcher.match(digit, scene, scale=1)
            if candidates:
                _, conf_white = max(candidates, key=lambda k: k[1])
            else:
                conf_white = 0

            conf_array[n] = max(conf_black, conf_white)

        return max(range(10), key=lambda n: conf_array[n])

    def get_frame_time(self, frame):
        """Read the timestamp of this frame.
        """
        thresh_min = 200
        _, frame = cv2.threshold(frame, thresh_min, 255, cv2.THRESH_TOZERO)

        boxes = [Rect(58, 245, 28, 26),
                 Rect(58, 273, 28, 26),
                 Rect(58, 315, 28, 26),
                 Rect(58, 343, 28, 26),
                 Rect(64, 377, 23, 21),
                 Rect(64, 398, 23, 21)
                 ]
        digits = [None for box in boxes]

        small = [False, False, False, False, True, True]

        for idx, _ in enumerate(digits):
            mask = boxes[idx].to_mask(528, 643, color=False)

            digits[idx] = self.match_digit(frame * mask, small=small[idx])

        if None not in digits:
            return "".join(str(d) for d in digits)

        return None


def __main__():
    mfs = MeleeFrameSync('samples/zelda-ic-fd.avi')
    realtimes = timer_values()
    realtime = next(realtimes)

    for _ in range(103):
        frame = mfs.get_frame()

    for _ in range(1000):
        frame = mfs.get_frame()
        time = mfs.get_frame_time(frame)
        print(time, realtime, distance(time, realtime))

        realtime = next(realtimes)


if __name__ == '__main__':
    __main__()
