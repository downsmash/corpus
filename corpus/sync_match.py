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
    return len(time) == 6 and (int(time[4:]) in VALID_FRAMES)

def distance(fr, to):
    if not (is_valid(fr) and is_valid(to)):
        return None

    minutes = int(to[:2]) - int(fr[:2])
    seconds = int(to[2:4]) - int(fr[2:4])
    frames = VALID_FRAMES.index(int(to[4:])) - VALID_FRAMES.index(int(fr[4:]))

    return minutes * 60 * 60 + seconds * 60 - frames

def get_digit_image(n, small=False, color=False, white=False):
    """Return the asset corresponding to the appropriate timer digit as an
    OpenCV-compatible array.
    """
    if n not in range(10):
        return None

    if white:
        path = resource_string("times", "{0}_time_white.png".format(n))
    else:
        path = resource_string("times", "{0}_time_small.png".format(n))

    nparr = np.frombuffer(path, np.uint8)
    img = cv2.imdecode(nparr, 1)

    if not color:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

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
    def __init__(self, filename):
        super().__init__(filename)

    @staticmethod
    def get_frame_time(frame):
        """Read the timestamp of this frame.
        """
        matcher = TemplateMatcher(debug=False, worst_match=0.45, criterion=cv2.TM_CCORR_NORMED)

        thresh_min = 200
        _, frame = cv2.threshold(frame, thresh_min, 255, cv2.THRESH_TOZERO)

        digits = [None] * 6
        boxes = [Rect(78, 515, 41, 42),
                 Rect(78, 558, 41, 42),
                 Rect(78, 621, 41, 42),
                 Rect(78, 663, 41, 42),
                 Rect(89, 718, 29, 28),
                 Rect(89, 749, 29, 31)
                 ]
        small = [False, False, False, False, True, True]

        for idx, _ in enumerate(digits):
            mask = boxes[idx].to_mask(720, 1280, color=False)

            conf_array = [0 for _ in range(10)]
            for n in range(10):
                digit = get_digit_image(n, color=False)
                digit = cv2.resize(digit, (0, 0), fx=39/37, fy=1)
                # _, digit = cv2.threshold(digit, thresh_min, 255, cv2.THRESH_TOZERO)

                if small[idx]:
                    scale = 27/24
                else:
                    scale = 37/24
                _, candidates = matcher.match(digit, frame * mask, scale=scale)

                if candidates:
                    _, best_conf = max(candidates, key=lambda k: k[1])

                    conf_black = best_conf

                digit = get_digit_image(n, color=False, white=True)
                digit = cv2.resize(digit, (0, 0), fx=39/37, fy=1)
                # _, digit = cv2.threshold(digit, thresh_min, 255, cv2.THRESH_TOZERO)

                if small[idx]:
                    scale = 27/24
                else:
                    scale = 37/24
                _, candidates = matcher.match(digit, frame * mask, scale=scale)

                if candidates:
                    _, best_conf = max(candidates, key=lambda k: k[1])

                    conf_white = best_conf

                conf_array[n] = max(conf_black, conf_white)

            digits[idx] = max(range(10), key=lambda n: conf_array[n])
            print(digits[idx], ("{:.3f}\t"*10).format(*conf_array))

        if None not in digits:
            return "".join(str(d) for d in digits)

    def read_frames(self):
        for _ in range(1000):
            yield self.get_frame_time(self.get_frame(color=False))


def main():
    mfs = MeleeFrameSync('samples/slippi_test.mp4')
    realtimes = timer_values()
    realtime = next(realtimes)

    while realtime != '075761':
        realtime = next(realtimes)

    for time in mfs.read_frames():
        print(realtime, time, distance(realtime, time), flush=True)
        realtime = next(realtimes)


if __name__ == '__main__':
    main()
