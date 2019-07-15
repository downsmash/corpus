"""
"""

from argparse import ArgumentParser
import re
from functools import lru_cache

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
                9,  7,  6,  4,  2,  0]

VALID_FRAMES_REGEX = re.compile(r'^0[0-7][0-5]\d([5-9][134689]|[1-4][124679]|0[024679])$')


def is_valid(time):
    """Return whether the given string represents a frame that can occur
    on Melee's timer.

    We require the first digit to be a 0 for now because it always should be.

    Parameters
    ----------
    time : str
        A string.
    """
    return (time is not None and
            re.match(VALID_FRAMES_REGEX, time))


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


@lru_cache(maxsize=None)
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
    at the frame after `start_time` seconds and counting down.

    I haven't timed the countdown from 5 seconds to 0. Presumably it remains
    at 60 fps.
    """
    minutes, seconds = start_time // 60, int(start_time) % 60
    centis = 0

    for seconds_left in range(start_time - 1, 5 - 1, -1):
        minutes, seconds = seconds_left // 60, int(seconds_left) % 60

        for centis in VALID_FRAMES:
            # 00:05.00 is not shown.
            if seconds_left == 5 and centis == 0:
                return

            yield "{:02d}{:02d}{:02d}".format(minutes, seconds, centis)


class MeleeFrameSync(StreamParser):
    """
    """
    @staticmethod
    def match_digit(scene, small=False, mask=None):
        """Given a masked frame, estimate the uncovered digit.
        """
        matcher = TemplateMatcher(worst_match=0.4)

        conf_array = [0 for n in range(10)]

        def get_digit_conf(digit):
            _, candidates = matcher.match(digit, scene, scale=1, mask=mask,
                                          cluster=False)
            if candidates:
                _, conf = max(candidates, key=lambda k: k[1])
            else:
                conf = 0

            return conf

        for digit in range(10):
            conf_black = get_digit_conf(get_digit_image(digit, small=small))

            conf_white = get_digit_conf(get_digit_image(digit, small=small,
                                                        white=True))

            conf_array[digit] = max(conf_black, conf_white)

        choice = max(range(10), key=lambda n: conf_array[n])
        # print(choice, ("{:.03f}\t"*10).format(*conf_array))

        if conf_array[choice] > matcher.worst_match:
            return choice
        return None

    def get_frame_time(self, frame):
        """Read the timestamp of this frame.
        """
        thresh_min = 200
        _, frame = cv2.threshold(frame, thresh_min, 255, cv2.THRESH_TOZERO)

        boxes = [Rect(56, 243, 32, 30),
                 Rect(56, 271, 32, 30),
                 Rect(56, 313, 32, 30),
                 Rect(56, 341, 32, 30),
                 Rect(62, 375, 27, 25),
                 Rect(62, 396, 27, 25)
                 ]
        small = [False, False, False, False, True, True]

        digits = [self.match_digit(frame, small=s, mask=box)
                  for s, box in zip(small, boxes)]

        if None not in digits:
            return "".join(str(d) for d in digits)

        return None

    def sync_frames(self):
        """
        """
        time = None
        frame_count = 0
        while time != "075999":
            frame = self.get_frame()
            frame_count += 1
            time = self.get_frame_time(frame)

        print("Found match start after {0} frames.".format(frame_count))

        frames_behind = 0

        for realtime in timer_values():
            dist = distance(time, realtime)
            if dist is None:
                pass
            elif dist == frames_behind:
                yield (frame_count, frames_behind)
            elif dist - frames_behind == -1:
                print("Repeated frame {0} ({1} frames behind)"
                      .format(frame_count, dist))
                frames_behind = dist
            elif 30 > dist - frames_behind > 0:
                print("Skipped {0} frame{1} after frame {2} ({3} frames behind)"
                      .format(dist - frames_behind,
                              "s" if dist - frames_behind > 1 else "",
                              frame_count,
                              dist))
                frames_behind = dist

            frame = self.get_frame()
            frame_count += 1
            time = self.get_frame_time(frame)


def __main__():
    parser = ArgumentParser()
    parser.add_argument("video", metavar="match.avi",
                        help=("the Slippi video file to be synced "
                              "(must be 643x528)"))
    parser.add_argument("frames", nargs="?", type=int, default=600,
                        help="the number of frames to read (default is 600)")

    args = parser.parse_args()

    mfs = MeleeFrameSync(args.video).sync_frames()

    for _ in range(args.frames):
        _ = next(mfs)


if __name__ == "__main__":
    __main__()
