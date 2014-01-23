import math
import sys
import subprocess
import time

from copy import copy

import Leap

WORKSPACE_COLS = 2
WORKSPACE_TOTAL = 4
GESTURE_SLEEP = 1


class LeapListener(Leap.Listener):
    gestures_lock_time = 0

    def on_connect(self, controller):
        # Enable gestures
        controller.enable_gesture(Leap.Gesture.TYPE_CIRCLE)
        controller.enable_gesture(Leap.Gesture.TYPE_SWIPE)

    def get_current_workspace(self):
        p1 = subprocess.Popen(['wmctrl', '-d'], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['awk', "/\*/ {print $1}"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        return int(''.join([i for i in p2.communicate()[0] if i.isdigit()]))

    def _find_in_haystack(self, haystack, needle):
        for k, v in enumerate(haystack):
            if needle == v:
                return k
            try:
                if needle in v:
                    return k
            except TypeError:
                continue

    def get_position(self, haystack, needle):
        y = self._find_in_haystack(haystack, needle)
        return [self._find_in_haystack(haystack[y], needle), y]

    def generate_workspace_matrix(self, num_total, num_cols):
        def chunks(l, n):
            """
            Yield successive n-sized chunks from l.
            """
            for i in xrange(0, len(l), n):
                yield l[i:i+n]
        chunk_size = math.ceil(num_total / float(num_cols))
        return list(chunks(range(num_total), int(chunk_size)))

    def find_new_position(self, workspaces, current_position, direction):
        move = 0, 0
        if direction[0] > 0.5:
            # move right
            move = 1, 0
        elif direction[0] < -0.5:
            # move left
            move = -1, 0
        elif direction[1] > 0.5:
            # move up
            move = 0, -1
        elif direction[1] < -0.5:
            # move down
            move = 0, 1

        new_position = copy(current_position)
        for k, v in enumerate(move):
            new_position[k] += v

        try:
            self.get_workspace_by_position(workspaces, new_position)
        except IndexError:
            del new_position
            return current_position
        else:
            del current_position
            return new_position

    def get_workspace_by_position(self, workspaces, position):
        return workspaces[position[1]][position[0]]

    def move_to_workspace(self, workspace_id):
        subprocess.call(['wmctrl', '-s', str(workspace_id)])

    def lock_screen(self):
        subprocess.Popen(['qdbus', 'org.freedesktop.ScreenSaver', '/ScreenSaver', 'Lock'])

    def lock_gestures(self):
        self.gestures_lock_time = time.time()

    def check_gestures_timeout(self):
        if self.gestures_lock_time:
            now = time.time()
            if now - self.gestures_lock_time >= 1:
                self.gestures_lock_time = 0
                return True
            return False
        return True

    def on_frame(self, controller):
        # Get the most recent frame and report some basic information
        frame = controller.frame()

        if not frame.hands.is_empty:
            # Get the first hand
            hand = frame.hands[0]

            # Check if the hand has any fingers
            fingers = hand.fingers

            # Gestures
            gesture_found = False
            if self.check_gestures_timeout():
                for gesture in frame.gestures():
                    if gesture.type == Leap.Gesture.TYPE_SWIPE and len(fingers) in (4, 5):
                        swipe = Leap.SwipeGesture(gesture)
                        workspaces = self.generate_workspace_matrix(WORKSPACE_TOTAL, WORKSPACE_COLS)
                        current_position = self.get_position(workspaces, self.get_current_workspace())
                        new_position = self.find_new_position(workspaces, current_position, swipe.direction)
                        new_workspace = self.get_workspace_by_position(workspaces, new_position)
                        self.move_to_workspace(new_workspace)
                        gesture_found = True
                    if gesture.type == Leap.Gesture.TYPE_CIRCLE and len(fingers) == 1:
                        self.lock_screen()
                        gesture_found = True

            if gesture_found:
                self.lock_gestures()

        if not (frame.hands.is_empty and frame.gestures().is_empty):
            pass

    def state_string(self, state):
        if state == Leap.Gesture.STATE_START:
            return "STATE_START"

        if state == Leap.Gesture.STATE_UPDATE:
            return "STATE_UPDATE"

        if state == Leap.Gesture.STATE_STOP:
            return "STATE_STOP"

        if state == Leap.Gesture.STATE_INVALID:
            return "STATE_INVALID"


def main():
    # Create a sample listener and controller
    listener = LeapListener()
    controller = Leap.Controller()

    # Have the sample listener receive events from the controller
    controller.add_listener(listener)

    # Keep this process running until Enter is pressed
    print "Press Enter to quit..."
    sys.stdin.readline()

    # Remove the sample listener when done
    controller.remove_listener(listener)


if __name__ == "__main__":
    main()
