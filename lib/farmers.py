from yaml import safe_load
from lib.models import Directory, Pool, session

class Farmer():
    def __init__(self, ip, text):
        self.ip = ip
        self.text = "\n".join(text)
        self.directories = []
        self.unused = []

    def parse(self):
        pass

    def analyze(self):
        dirs = session.query(Directory).filter(Directory.ip==self.ip).all()
        for dir in dirs:
            if dir.path in self.directories:
                dir.used += 1
            else:
                self.unused.append(dir.path)

    def cache(self, pool):
        session.query(Pool).filter(Pool.ip==self.ip, Pool.pool==pool).delete()
        if len(self.unused):
            errors = "\n".join(self.unused)
        else:
            errors = None
        farmer = Pool(ip=self.ip, pool=pool, errors=errors)
        session.add(farmer)
        session.commit()

class Flexpool(Farmer):
    def parse(self):
        config = safe_load(self.text)
        self.directories = config.get('plot_directories')

    @staticmethod
    def search_config(ssh):
        # Flexfarmer installed only in this directory
        f = '/root/flexfarmer/config.yml'
        test = ssh.cmd(f"ls {f} 2>/dev/null")
        if len(test) == 1:
            return f
        return False

class Hpool(Farmer):
    def parse(self):
        config = safe_load(self.text)
        self.directories = config.get('path')

    @staticmethod
    def search_conf(ssh):
        # Hpool was installed to random directories
        # Config pathes are different.
        sf = ssh.cmd("ls /etc/systemd/system/ | grep hpool")
        if len(sf) == 0:
            return False
        x = ssh.cmd(f"cat /etc/systemd/system/{sf[0]} | grep ExecStart")
        p = x[0].split("=")[1]
        d = '/'.join(p.split('/')[:-1])
        f = d + '/config.yaml'
        test = ssh.cmd(f"ls {f}")
        if len(test) == 1:
            return f
        return False