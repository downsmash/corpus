"""
"""
from argparse import ArgumentParser

from slippi import Game

from sync_match import MeleeFrameSync


def __main__():
    parser = ArgumentParser(description=("Generate training images from a "
                                         "Project Slippi replay."))
    parser.add_argument("--ports", action="store_true", default=True,
                        help=("grab the used port (stock/percent) displays "
                              "(default: True)"))
    parser.add_argument("--filetype", default="TIF",
                        help="the filetype of output images (default: TIF)")
    parser.add_argument("replay", metavar="match.slp", type=str,
                        help="a Project Slippi game data file")
    parser.add_argument("video", metavar="match.avi", type=str,
                        help="a 643x528 Dolphin framedump of `match.slp`")
    parser.add_argument("outdir", type=str,
                        help="the directory to save files to")

    args = parser.parse_args()

    game = Game(args.replay)
    stream = MeleeFrameSync(args.video)


if __name__ == "__main__":
    __main__()
