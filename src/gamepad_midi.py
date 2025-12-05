#!/usr/bin/env python3
import pygame
import mido
import sys

# ================== CONFIGURATION ==================
DEADZONE = 0.15                     # Smaller deadzone feels more responsive for momentary
MIDI_CHANNEL = 0
DESIRED_PORT_NAME = "Xbox In"  # CHECK YOUR PORT NAME - I use loopMIDI for MIDI mapping

# 8 independent joystick directions — now momentary (0 when released)
CC_JOY = {
    'left_right':  1,
    'left_left':   2,
    'left_down':   3,
    'left_up':     4,
    'right_right':10,
    'right_left': 11,
    'right_down': 12,
    'right_up':   13,
}

CC_BUTTONS = [20,21,22,23,24,25,26,27,28,29] + [None]*10
CC_LEFT_TRIGGER  = 5   # now momentary
CC_RIGHT_TRIGGER = 6   # now momentary

CC_DPAD = { (0,1):70, (0,-1):71, (-1,0):72, (1,0):73,
            (1,1):74, (1,-1):75, (-1,1):76, (-1,-1):77 }

class GamepadToMomentaryMIDI:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            print("No gamepad found!")
            sys.exit(1)
        self.joy = pygame.joystick.Joystick(0)
        self.joy.init()
        print(f"Gamepad: {self.joy.get_name()}")

        ports = mido.get_output_names()
        if not ports:
            print("No MIDI ports!")
            sys.exit(1)
        port = next((p for p in ports if DESIRED_PORT_NAME.lower() in p.lower()), ports[0])
        self.outport = mido.open_output(port)
        print(f"MIDI → {port}\n")

        # We keep track of what we last sent so we only send when something actually changes
        self.last_joy = {k: 0 for k in CC_JOY.keys()}
        self.last_lt = 0
        self.last_rt = 0

    def send(self, cc, value):
        msg = mido.Message('control_change', channel=MIDI_CHANNEL, control=cc, value=value)
        self.outport.send(msg)

    def update_stick(self, x_axis, y_axis, prefix):
        x = self.joy.get_axis(x_axis)
        y = self.joy.get_axis(y_axis)

        # Right / Left
        right_val = int(max(0, x) * 127) if abs(x) >= DEADZONE else 0
        left_val  = int(max(0, -x) * 127) if abs(x) >= DEADZONE else 0

        # Up / Down (note Y axis is inverted on most controllers)
        down_val  = int(max(0,  y) * 127) if abs(y) >= DEADZONE else 0
        up_val    = int(max(0, -y) * 127) if abs(y) >= DEADZONE else 0

        # Send only on change
        if right_val != self.last_joy[f'{prefix}_right']:
            self.send(CC_JOY[f'{prefix}_right'], right_val)
            self.last_joy[f'{prefix}_right'] = right_val
        if left_val != self.last_joy[f'{prefix}_left']:
            self.send(CC_JOY[f'{prefix}_left'], left_val)
            self.last_joy[f'{prefix}_left'] = left_val
        if down_val != self.last_joy[f'{prefix}_down']:
            self.send(CC_JOY[f'{prefix}_down'], down_val)
            self.last_joy[f'{prefix}_down'] = down_val
        if up_val != self.last_joy[f'{prefix}_up']:
            self.send(CC_JOY[f'{prefix}_up'], up_val)
            self.last_joy[f'{prefix}_up'] = up_val

    def update_triggers(self):
        # Xbox triggers: axis 2 = LT, axis 5 = RT  →  -1.0 (rest) … +1.0 (fully pressed)
        lt = self.joy.get_axis(2)
        rt = self.joy.get_axis(5)

        # Momentary: only send >0 when actually pressed, otherwise 0
        lt_val = int((lt + 1) * 63.5) if lt > -0.8 else 0   # small threshold to avoid floating-point noise
        rt_val = int((rt + 1) * 63.5) if rt > -0.8 else 0

        if lt_val != self.last_lt:
            self.send(CC_LEFT_TRIGGER, lt_val)
            self.last_lt = lt_val
        if rt_val != self.last_rt:
            self.send(CC_RIGHT_TRIGGER, rt_val)
            self.last_rt = rt_val

    def run(self):
        clock = pygame.time.Clock()
        print("Gamepad → Momentary MIDI CC READY! (all sticks + triggers are momentary)\n")

        try:
            while True:
                for event in pygame.event.get():
                    # Buttons (already momentary)
                    if event.type == pygame.JOYBUTTONDOWN and event.button < len(CC_BUTTONS) and CC_BUTTONS[event.button]:
                        self.send(CC_BUTTONS[event.button], 127)
                    if event.type == pygame.JOYBUTTONUP and event.button < len(CC_BUTTONS) and CC_BUTTONS[event.button]:
                        self.send(CC_BUTTONS[event.button], 0)

                    # D-pad / Hat (already momentary)
                    if event.type == pygame.JOYHATMOTION:
                        # Turn off previous direction
                        if hasattr(self, 'last_hat') and self.last_hat in CC_DPAD:
                            self.send(CC_DPAD[self.last_hat], 0)
                        # Turn on new direction (if any)
                        if event.value != (0,0) and event.value in CC_DPAD:
                            self.send(CC_DPAD[event.value], 127)
                        self.last_hat = event.value

                # Continuously poll sticks and triggers (this is where momentary behavior happens)
                self.update_stick(0, 1, 'left')   # Left stick
                self.update_stick(3, 4, 'right')  # Right stick
                self.update_triggers()

                clock.tick(200)  # 200 Hz is more than enough, reduces MIDI spam

        except KeyboardInterrupt:
            print("\nBye!")
        finally:
            pygame.quit()

if __name__ == "__main__":
    GamepadToMomentaryMIDI().run()
