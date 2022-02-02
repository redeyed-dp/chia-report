import shutil
import colorama
from colorama import Fore, Back, Style

class Message():
    def __init__(self):
        self.width = shutil.get_terminal_size()[0]
        self.offset = 0
        colorama.init(autoreset=True)

    def task(self, message, back=None, fore=None):
        b = ''
        f = ''
        if back:
            b = getattr(Back, back.upper())
        if fore:
            f = getattr(Fore, fore.upper())
        print(b + f + message, end='')
        self.offset = self.width - len(message)

    def ok(self):
        print (Fore.GREEN + "OK".rjust(self.offset))

    def error(self):
        print(Fore.RED + "ERROR".rjust(self.offset))