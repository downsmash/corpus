from slippi import Game
import cv2
from re import search

game = Game('match-dk.slp')
vc = cv2.VideoCapture('dk.avi')

with open('dk.log') as f:
    lines = f.read().split('\n')
    dropped_frames = [line for line in lines if search("frame \d+", line)]
    dropped_frames = [int(search("frame (\d+)", line).group(1)) for line in dropped_frames]

print(dropped_frames)

print(vc.get(7), len(game.frames))

def frames(vc, offset=-31):
    n = 0
    success = True
    while success:
        if offset < 0:
            yield None
            offset += 1
            continue
        else:
            n += 1
        success, frame = vc.read()
        # print(n)
        if n >= offset:
            if n % 110 == 55:
                # yield None
                pass
            yield frame

def data_from_frame(frame):
    data = []
    for port in frame.ports:
        if port is None:
            data.append(None)
        else:
            data.append((port.leader.post.stocks, port.leader.post.damage, port.leader.post.state))
    return data

offset = min(dropped_frames)
dropped_frames = [d for d in dropped_frames if d > offset]

n = 0
for frame, data in zip(frames(vc), game.frames):
    if frame is not None:
        n += 1
        dropped_count = len([x for x in dropped_frames if x - offset <= n])
        if (data.index + dropped_count - 59) % 60 == 0:
            cv2.putText(frame, str(n), (10, 30), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 0))
            ports = frame[395:490,:,:]
            print(n, data.index, data_from_frame(data))
            cv2.imshow('ports', frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
