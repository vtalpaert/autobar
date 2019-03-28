import weakref

import pygame

try:
    from hardware.background_threads import BackgroundThread, Event
except ImportError:
    from background_threads import BackgroundThread, Event


class Joystick(BackgroundThread):
    def __init__(self, parent, on_pressed: str, on_released: str, name: str=None, wait: float=0.0):
        self._init_joystick(name)
        super(Joystick, self).__init__(target=self.read)
        self.wait = float(wait)
        #self.full = Event()
        self.parent = weakref.proxy(parent)
        self.on_pressed = on_pressed
        self.on_released = on_released

    def _init_joystick(self, name):
        pygame.init()
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()
        for joy in range(joystick_count):
            self.joystick = pygame.joystick.Joystick(joy)
            self.joystick.init()
            self.joystick_name = self.joystick.get_name()
            if name == self.joystick_name:
                break
        if name and name != self.joystick_name:
            raise ValueError("Did not find %s" % name)

    def read(self):
        try:
            while not self.stopping.wait(self.wait):
                for event in pygame.event.get():
                    # Possible joystick actions: JOYAXISMOTION JOYBALLMOTION JOYBUTTONDOWN JOYBUTTONUP JOYHATMOTION
                    if event.type == pygame.JOYBUTTONDOWN:
                        getattr(self.parent, self.on_pressed)(event.button)
                    elif event.type == pygame.JOYBUTTONUP:
                        getattr(self.parent, self.on_released)(event.button)
        except ReferenceError:
            # Parent is dead; time to die!
            self.quit()

    def quit(self):
        pygame.quit()


class TestInterface(object):
    def __init__(self, name):
        self.buttons = dict([(i, False) for i in range(2, 12)])
        self.joy = Joystick(self, name=name, on_pressed="button_pressed", on_released="button_released")
        self.joy.start()

    def button_pressed(self, button):
        self.buttons[button] = True
        print(self.buttons)

    def button_released(self, button):
        self.buttons[button] = False
        print(self.buttons)


if __name__ == '__main__':
    test = TestInterface("DragonRise Inc.   Generic   USB  Joystick  ")
    while True:
        pass
