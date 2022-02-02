import logging
from lib.messages import Message
from colorama import Fore, Style
from lib.parsers import hosts, Lsblk, Df, Lshw, Blkid, Etcfstab, Search
from lib.farmers import Flexpool, Hpool
from lib.ssh import SshConn

logging.basicConfig(filename='scan.log', filemode='w', format='%(levelname)s:%(message)s')
m = Message()
ssh_errors = []
def scan_host(ip, hostname):
    m.task(f"Подключаюсь к {hostname.upper()}...", back='green')
    ssh = SshConn(ip=ip)
    if ssh.conect():
        m.ok()
    else:
        ssh_errors.append(ip)
        m.error()
        return
    m.task("Выполняю lsblk...")
    try:
        lsblk = Lsblk(ip=ip, text=ssh.cmd("/usr/bin/lsblk"))
        lsblk.parse()
        lsblk.cache()
        m.ok()
    except Exception as e:
        m.error()
        logging.error(e)
    m.task("Выполняю lshw... ")
    try:
        lshw = Lshw(ip=ip, text=ssh.cmd("/usr/bin/lshw -c disk"))
        lshw.parse()
        lshw.cache()
        m.ok()
    except Exception as e:
        m.error()
        logging.error(e)
    m.task("Определяю UUID разделов...")
    blkid = Blkid(ip=ip)
    for disk in lsblk.disks:
        for part in lsblk.disks[disk]['partitions']:
            blkid.parse(part=part, text=ssh.cmd(f"/usr/sbin/blkid /dev/{part}"))
    blkid.cache()
    m.ok()
    m.task("Определяется свободное место...")
    dfh = Df(ip=ip, text=ssh.cmd("/usr/bin/df -H"))
    dfh.parse()
    dfh.cache()
    m.ok()
    m.task("Читаю FSTAB...")
    try:
        fstab = Etcfstab(ip=ip, text=ssh.cmd("cat /etc/fstab"))
        fstab.parse()
        fstab.analyze()
        fstab.cache()
        m.ok()
    except Exception as e:
        logging.error(e)
        m.error()
    m.task("Поиск плотов...")
    try:
        search = Search(ip=ip, text=ssh.cmd("find /mnt -name *.plot"))
        search.parse()
        search.cache()
        m.ok()
    except Exception as e:
        logging.error(e)
        m.error()
    m.task("Анализ сервиса hpool...")
    try:
        file = Hpool.search_conf(ssh)
        if file:
            hpool = Hpool(ip=ip, text=ssh.cmd(f"cat {file}"))
            hpool.parse()
            hpool.analyze()
            hpool.cache('hpool')
        m.ok()
    except Exception as e:
        logging.error(e)
        m.error()
    m.task("Анализ сервиса flexpool...")
    try:
        file = Flexpool.search_config(ssh)
        if file:
            flexpool = Flexpool(ip=ip, text=ssh.cmd(f"cat {file}"))
            flexpool.parse()
            flexpool.analyze()
            flexpool.cache('flexpool')
        m.ok()
    except Exception as e:
        logging.error(e)
        m.error()
    ssh.disconect()


def scan_all():
    h = hosts()
    for ip in h:
        scan_host(ip, h[ip])

def rescan():
    h = hosts()
    tmp = ssh_errors.copy()
    for ip in tmp:
        ssh_errors.remove(ip)
        scan_host(ip, h[ip])

complete = False
while True:
    print(Fore.CYAN + "Выберите действие:")
    if not complete:
        print(Fore.CYAN + " a" + Style.RESET_ALL + " - Сканировать все сервера")
    if len(ssh_errors):
        print(Fore.CYAN + " r" + Style.RESET_ALL + " - Повторно сканировать сбойные сервера")
    if complete:
        print(Fore.CYAN + " t" + Style.RESET_ALL + " - Вывести отчет в терминал")
    print(Fore.CYAN + " q " + Style.RESET_ALL + "- Выйти")

    a = input(Fore.CYAN + ">>> ").lower()
    print(Style.RESET_ALL)
    if a == 'q':
        break
    elif a == 'a':
        scan_all()
        complete = True
    elif a == 'r':
        if len(ssh_errors):
            rescan()
        else:
            print(Fore.RED + "Нет серверов для повторного сканирования")
    elif a == 't':
        pass
    else:
        print(Fore.RED + f"Неверная опция {a}")