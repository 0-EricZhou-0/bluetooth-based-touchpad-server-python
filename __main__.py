import time
import uuid
import threading

from bluetooth import *
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

global server_sock, client_sock, CONST, mouse, keyboard


def constant(f):
    def f_set(self, value):
        raise TypeError

    def f_get(self):
        return f(self)

    return property(f_get, f_set)


class _Const(object):
    @constant
    def parameter_separator(self): return '\\t'

    @constant
    def line_separator(self): return '\\n'

    @constant
    def MOVE_LEFT(self): return 3

    @constant
    def MOVE_RIGHT(self): return 4

    @constant
    def MOVE_UP(self): return 5

    @constant
    def MOVE_DOWN(self): return 6

    @constant
    def CLICK(self): return 1

    @constant
    def RIGHT_CLICK(self): return 2

    @constant
    def DOUBLE_CLICK(self): return 3

    @constant
    def MOVE_CURSOR_RELATIVE(self): return 4

    @constant
    def MOVE_CURSOR_ABSOLUTE(self): return 5

    @constant
    def SELECT(self): return 6

    @constant
    def SCROLL(self): return 7

    @constant
    def UNDO(self): return 8

    @constant
    def COPY(self): return 9

    @constant
    def PASTE(self): return 10

    @constant
    def CUT(self): return 11

    @constant
    def RETURN_TO_DESKTOP(self): return 12

    @constant
    def ENABLE_TASK_MODE(self): return 13

    @constant
    def SWITCH_APPLICATION(self): return 14

    @constant
    def SWITCH_TAB(self): return 15

    @constant
    def INPUT_CHARACTER(self): return 16

    @constant
    def CANCEL_LAST_ACTION_FUNCTIONAL(self): return 100

    @constant
    def HEARTBEAT_FUNCTIONAL(self): return 101

    @constant
    def ACTION_NOT_FOUND_FUNCTIONAL(self): return 102

    @constant
    def EXITING_TOUCH_PAD_FUNCTIONAL(self): return 103


class SwitchException(Exception):
    pass


class Mouse:
    __scroll_thread = None
    __scroll_tolerance = 10
    __scroll_resistance = 1.5
    __scroll_momentum_x = 0
    __scroll_momentum_y = 0
    __scroll_timeout = 0

    def __init__(self):
        self.__mouse = MouseController()
        self.__is_dragging = False

    def drag_or_release(self):
        if self.__is_dragging:
            self.__mouse.release(Button.left)
        else:
            self.__mouse.press(Button.left)
        self.__is_dragging = not self.__is_dragging

    def click(self, button, times):
        self.__mouse.click(button, times)

    def move(self, delta_x, delta_y, delay=0):
        if delay == 0:
            thread = threading.Thread(target=mouse.move, args=(delta_x, delta_y, 0.05))
            thread.start()
        time.sleep(delay)
        self.__mouse.move(delta_x, delta_y)

    def position(self, x, y):
        self.__mouse.position(x, y)

    def scroll(self, delta_x, delta_y):
        if self.__scroll_thread is None:
            print("new scroll thread created")
            self.__scroll_thread = threading.Thread(target=self.__scroll_with_inertia)
            self.__scroll_thread.start()
        if delta_x * self.__scroll_momentum_x < 0:
            self.__scroll_momentum_x = 0
        else:
            self.__scroll_momentum_x += delta_x
        if delta_y * self.__scroll_momentum_y < 0:
            self.__scroll_momentum_y = 0
        else:
            self.__scroll_momentum_y += delta_y

    def __scroll_with_inertia(self):
        while self.__scroll_timeout < 3:
            time.sleep(0.1)
            if self.__scroll_momentum_x == 0 and self.__scroll_momentum_y == 0:
                self.__scroll_timeout += 0.1
                continue
            threading.Thread(target=self.__scroll_with_delay,
                             args=(self.__scroll_momentum_x, -self.__scroll_momentum_y)).start()

            self.__scroll_momentum_x /= self.__scroll_resistance
            self.__scroll_momentum_y /= self.__scroll_resistance
            if abs(self.__scroll_momentum_x) < self.__scroll_tolerance:
                self.__scroll_momentum_x = 0
            if abs(self.__scroll_momentum_y) < self.__scroll_tolerance:
                self.__scroll_momentum_y = 0
        self.__scroll_thread = None
        self.__scroll_timeout = 0
        print("new scroll thread terminated")

    def __scroll_with_delay(self, momentum_x, momentum_y):
        times = 10
        delay = 0.1 / times
        print(delay, momentum_x / times, momentum_y / times)
        for _ in range(times):
            self.__mouse.scroll(momentum_x / times, momentum_y / times)
            time.sleep(delay)


class Keyboard:
    def __init__(self):
        self.__keyboard = KeyboardController()
        self.__stored_key_list = []

    def release_all(self):
        for button in self.__stored_key_list:
            self.__keyboard.release(button)
        self.__stored_key_list.clear()

    def press_key_release(self, button):
        self.__keyboard.press(button)
        self.__keyboard.release(button)

    def press_key_store(self, button):
        if button not in self.__stored_key_list:
            self.__stored_key_list.append(button)
            self.__keyboard.press(button)

    def stored_key_release(self, button):
        if button in self.__stored_key_list:
            self.__stored_key_list.remove(button)
            self.__keyboard.release(button)

    def switch_application(self, direction):
        self.press_key_store(Key.alt)
        if direction == CONST.MOVE_RIGHT:
            self.stored_key_release(Key.shift)
        else:
            self.press_key_store(Key.shift)
        self.press_key_release(Key.tab)

    def switch_tab(self, direction):
        self.press_key_store(Key.ctrl)
        if direction == CONST.MOVE_RIGHT:
            self.stored_key_release(Key.shift)
        else:
            self.press_key_store(Key.shift)
        self.press_key_release(Key.tab)

    def return_to_desktop(self):
        self.press_key_store(Key.cmd)
        self.press_key_release('d')
        self.stored_key_release(Key.cmd)

    def enable_task_mode(self):
        self.press_key_store(Key.cmd)
        self.press_key_release(Key.tab)
        self.stored_key_release(Key.cmd)

    def undo(self):
        self.press_key_store(Key.ctrl)
        self.press_key_release('z')
        self.stored_key_release(Key.ctrl)

    def copy(self):
        self.press_key_store(Key.ctrl)
        self.press_key_release('c')
        self.stored_key_release(Key.ctrl)

    def paste(self):
        self.press_key_store(Key.ctrl)
        self.press_key_release('v')
        self.stored_key_release(Key.ctrl)

    def cut(self):
        self.press_key_store(Key.ctrl)
        self.press_key_release('x')
        self.stored_key_release(Key.ctrl)


def touch_pad_handle_message(message):
    separated_message = message.split(CONST.line_separator)
    for ele in separated_message:
        param_list = ele.split(CONST.parameter_separator)
        print(param_list)
        instruction = int(param_list[0])
        if instruction == CONST.CLICK:
            mouse.click(Button.left, 1)
        elif instruction == CONST.RIGHT_CLICK:
            mouse.click(Button.right, 1)
        elif instruction == CONST.DOUBLE_CLICK:
            mouse.click(Button.left, 2)
        elif instruction == CONST.MOVE_CURSOR_RELATIVE:
            mouse.move(int(param_list[1]), int(param_list[2]))
        elif instruction == CONST.MOVE_CURSOR_ABSOLUTE:
            mouse.position(int(param_list[1]), int(param_list[2]))
        elif instruction == CONST.SELECT:
            mouse.drag_or_release()
        elif instruction == CONST.SCROLL:
            mouse.scroll(int(param_list[1]) * 20, int(param_list[2]) * 10)
        elif instruction == CONST.UNDO:
            keyboard.undo()
        elif instruction == CONST.COPY:
            keyboard.copy()
        elif instruction == CONST.PASTE:
            keyboard.paste()
        elif instruction == CONST.CUT:
            keyboard.cut()
        elif instruction == CONST.RETURN_TO_DESKTOP:
            keyboard.return_to_desktop()
        elif instruction == CONST.ENABLE_TASK_MODE:
            keyboard.enable_task_mode()
        elif instruction == CONST.SWITCH_APPLICATION:
            keyboard.switch_application(int(param_list[1]))
        elif instruction == CONST.SWITCH_TAB:
            keyboard.switch_tab(param_list[1])
        # elif instruction == CONST.INPUT_CHARACTER:
        elif instruction == CONST.CANCEL_LAST_ACTION_FUNCTIONAL:
            keyboard.release_all()

        elif instruction == CONST.EXITING_TOUCH_PAD_FUNCTIONAL:
            raise SwitchException
        else:
            pass


def start_server():
    global server_sock, client_sock
    server_sock = BluetoothSocket(RFCOMM)
    server_sock.bind(("", PORT_ANY))
    server_sock.listen(1)
    server_uuid = "00001101-0000-1000-8000-00805F9B34FB"
    advertise_service(server_sock, "SampleServer",
                      service_id=server_uuid,
                      service_classes=[server_uuid, SERIAL_PORT_CLASS],
                      profiles=[SERIAL_PORT_PROFILE],
                      #                   protocols = [ OBEX_UUID ]
                      )
    print("Bluetooth address of this machine:\n" + ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                                                             for ele in range(0, 8 * 6, 8)][::-1]))
    print("Waiting for connection")

    client_sock, client_info = server_sock.accept()
    print("Accepted connection from ", client_info)


def receive_from_client():
    return str(client_sock.recv(1024))[2:-3]


def general_listen():
    try:
        while True:
            line_read = receive_from_client()
            if line_read == "TOUCH_PAD":
                print("TOUCH PAD SESSION START")
                try:
                    while True:
                        touch_pad_handle_message(receive_from_client())
                except SwitchException:
                    print("TOUCH PAD SESSION END")
            if line_read == "EXIT":
                break

    except IOError:
        print("IOError")


if __name__ == '__main__':
    CONST = _Const()
    mouse = Mouse()
    keyboard = Keyboard()

    start_server()
    general_listen()

    print("Disconnected")

    client_sock.close()
    server_sock.close()
    print("Socket closed")
