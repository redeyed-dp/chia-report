import re
from lib.models import Disk, Partition, Fstab, Directory, session

def hosts():
    hosts = {}
    try:
        file = open("hosts.txt")
        for s in file:
            if s and s[0] != '#':
                (ip, hostname) = s.strip().split(" ", maxsplit=2)
                hosts[ip] = hostname
    except:
        print("File with IP addresses list not found!")
        exit()
    file.close()
    return hosts

class Lsblk():
    def __init__(self, ip, text):
        self.ip = ip
        self.text = text
        self.disks = {}

    def parse(self):
        for s in self.text:
            ss = re.split(r' +', s.strip())
            # ZFS volumes doesn't exist any drive
            if ss[5] == 'disk' and not re.search(r'^zd', ss[0]):
                self.disks[ss[0]] = {'partitions': {}}
            if ss[5] == 'part':
                part = ss[0][2:]
                if part.startswith('sd'):
                    disk = part[:3]
                elif part.startswith('nvme'):
                    disk = part[:7]
                if self.disks.get(disk):
                    mp = ''
                    if len(ss) == 7:
                        mp = ss[6]
                    self.disks[disk]['partitions'][part] = {'size': ss[3], 'mount': mp}

    def cache(self):
        session.query(Disk).filter(Disk.ip==self.ip).delete()
        session.commit()
        for d in self.disks:
            disk = Disk(ip=self.ip, name=d)
            session.add(disk)
            session.commit()
            for p in self.disks[d]['partitions']:
                part = Partition(disk = disk.id,
                                 name = p,
                                 mountpoint = self.disks[d]['partitions'][p]['mount'],
                                 size = self.disks[d]['partitions'][p]['size'])
                session.add(part)
                session.commit()

class Df():
    def __init__(self, ip, text):
        self.ip = ip
        self.text = text
        self.disk = {}

    def parse(self):
        for s in self.text:
            ss = re.split(r' +', s.strip())
            part = ss[0].split('/')[-1]
            if part.startswith('sd') or part.startswith('nvme'):
                self.disk[part] = {'used':ss[2],
                                   'available': ss[3],
                                   'usage': int(ss[4].replace('%', ''))
                                   }

    def cache(self):
        for d in self.disk:
            part = session.query(Partition).outerjoin(Disk).filter(Disk.ip==self.ip, Partition.name==d).one_or_none()
            if part:
                for attr in ('used', 'available', 'usage'):
                    setattr(part, attr, self.disk[d].get(attr))
                session.commit()

class Lshw():
    def __init__(self, ip, text):
        self.ip = ip
        self.text = text
        self.disks = {}

    def parse(self):
        tmp = {}
        for s in self.text:
            if s.lstrip().startswith('*-'):
                if bool(tmp):
                    # Save values from previous iteration
                    ln = tmp.get('logical name') or tmp.get('логическое имя')
                    assert ln, f'WARNING! Unknown locale at {self.ip}'
                    ln = ln.replace('/dev/', '')
                    self.disks[ln] = {}
                    self.disks[ln]['size'] = tmp.get('size') or tmp.get('размер')
                    self.disks[ln]['description'] = tmp.get('description') or tmp.get('описание') or ''
                    self.disks[ln]['product'] = tmp.get('product') or tmp.get('продукт') or ''
                    self.disks[ln]['vendor'] = tmp.get('vendor') or tmp.get('производитель') or ''
                    self.disks[ln]['serial'] = tmp.get('serial') or tmp.get('серийный №') or ''
                tmp = {}
            else:
                param, value = s.split(': ', 2)
                tmp[param.lstrip()] = value.rstrip()

    def cache(self):
        for d in self.disks:
            try:
                disk = session.query(Disk).filter(Disk.ip==self.ip, Disk.name==d).one()
                for param in ('size', 'description', 'product', 'vendor', 'serial'):
                    setattr(disk, param, self.disks[d][param])
                session.commit()
            except Exception as e:
                print(e)

class Blkid():
    def __init__(self, ip):
        self.ip = ip
        self.disks = {}

    def parse(self, part, text):
        self.disks[part] = {}
        for tmp in text[0].split(" "):
            ss = tmp.split("=", 2)
            if ss[0] in ('UUID', 'PARTUUID', 'LABEL'):
                self.disks[part][ss[0].lower()] = ss[1].replace('"', '')

    def cache(self):
        for disk in self.disks:
            part = session.query(Partition).outerjoin(Disk).filter(Partition.name==disk, Disk.ip==self.ip).one()
            for param in ('uuid', 'partuuid', 'label'):
                setattr(part, param, self.disks[disk].get(param) or '')
            session.commit()

class Etcfstab():
    def __init__(self, ip, text):
        self.ip = ip
        self.text = text
        self.fstab = {}

    def parse(self):
        i = 1
        for s in self.text:
            # Cleared string
            cs = s.strip().replace('\t', ' ')
            if not s or s.startswith('#'):
                self.fstab[i] = {'type': 'comment', 'string': cs}
                i += 1
                continue
            ss = re.split(r'\s+', cs)
            if ss[0].startswith('UUID'):
                uuid = ss[0].split('=')[1].replace('"', '')
                self.fstab[i] = {'type': 'config', 'string': cs, 'uuid': uuid, 'mountpoint': ss[1]}
            elif ss[0].startswith('/dev/disk/by-uuid'):
                uuid = ss[0].replace('/dev/disk/by-uuid/', '')
                self.fstab[i] = {'type': 'config', 'string': cs, 'uuid': uuid, 'mountpoint': ss[1]}
            elif ss[0].startswith('/dev/disk/by-partuuid'):
                partuuid = ss[0].replace('/dev/disk/by-partuuid/', '')
                self.fstab[i] = {'type': 'config', 'string': cs, 'partuuid': partuuid, 'mountpoint': ss[1]}
            elif ss[0].startswith('/dev/'):
                part = ss[0].replace('/dev/', '')
                self.fstab[i] = {'type': 'config', 'string': cs, 'dev': part, 'mountpoint': ss[1]}
            else:
                self.fstab[i] = {'type': 'unknown', 'string': cs}
            i += 1

    def analyze(self):
        for i in self.fstab:
            if self.fstab[i]['type'] != 'config':
                continue
            # Search partition
            q = session.query(Partition).outerjoin(Disk)
            if self.fstab[i].get('dev'):
                q = q.filter(Partition.name == self.fstab[i]['dev'])
            elif self.fstab[i].get('uuid'):
                q = q.filter(Partition.uuid == self.fstab[i]['uuid'])
            elif self.fstab[i].get('partuuid'):
                q = q.filter(Partition.partuuid == self.fstab[i]['partuuid'])
            drive = q.filter(Disk.ip == self.ip).one_or_none()
            if drive:
                # Record exists to real partition
                drive.fstab += 1
                session.commit()
                # Few records for one partition
                if drive.fstab > 1:
                    self.fstab[i]['error'] = "Запись дублируется"
                # Current mountpoint doesn't exists defined in fstab
                # Partition was mounted manually
                if drive.mountpoint != self.fstab[i]['mountpoint']:
                    self.fstab[i]['error'] = f"Точка монтирования {drive.mountpoint} не соответствует указанной в fstab"
            else:
                drive = q.one_or_none()
                if drive:
                    # Drive with this UUID installed on another server
                    self.fstab[i]['error'] = f"Диск установлен на сервере {drive.ip}"
                else:
                    # Drive with this UUID is anywhere
                    self.fstab[i]['error'] = "Запись не соответствует ни одному диску"

    def cache(self):
        # Remove old records from cache
        session.query(Fstab).filter(Fstab.ip == self.ip).delete()
        for i in self.fstab:
            s = Fstab(ip = self.ip,
                      sn = i,
                      st = self.fstab[i]['type'],
                      ss = self.fstab[i]['string'],
                      error = self.fstab[i].get('error'))
            session.add(s)
        session.commit()

class Search():
    def __init__(self, ip, text):
        self.ip = ip
        self.text = text
        self.directories = set()

    def parse(self):
        for s in self.text:
            dir = '/'.join(s.split('/')[0:-1])
            self.directories.add(dir)

    def cache(self):
        session.query(Directory).filter(Directory.ip==self.ip).delete()
        session.commit()
        for path in self.directories:
            dir = Directory(ip = self.ip,
                            path = path)
            session.add(dir)
            session.commit()