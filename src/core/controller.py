import random
import time

import pydirectinput


def sleep_with_stop(seconds, is_running_check, granularity=0.1):
    end_time = time.time() + max(0, seconds)
    while time.time() < end_time:
        if not is_running_check():
            return False
        time.sleep(min(granularity, max(0, end_time - time.time())))
    return True


def human_click(x, y, is_running_check, move=True, offset=0):
    if not is_running_check():
        return False

    target_x = int(x + random.randint(-offset, offset)) if offset else int(x)
    target_y = int(y + random.randint(-offset, offset)) if offset else int(y)

    if move:
        pydirectinput.moveTo(target_x, target_y, duration=random.uniform(0.12, 0.24))
        if not sleep_with_stop(0.05, is_running_check):
            return False
        pydirectinput.moveRel(-random.randint(1, 4), random.randint(-1, 1))
        if not sleep_with_stop(0.04, is_running_check):
            return False

    pydirectinput.mouseDown()
    if not sleep_with_stop(random.uniform(0.05, 0.09), is_running_check):
        pydirectinput.mouseUp()
        return False
    pydirectinput.mouseUp()
    return sleep_with_stop(0.1, is_running_check)
