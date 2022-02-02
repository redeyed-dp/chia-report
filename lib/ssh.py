from paramiko import SSHClient, AutoAddPolicy, RSAKey

class SshConn():
    def __init__(self, ip, login="root", password=""):
        self.ip = ip
        self.login = login
        self.password = password

    def conect(self):
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        try:
            if self.password:
                self.ssh.connect(hostname=self.ip,
                                 username=self.login,
                                 password=self.password,
                                 look_for_keys=False,
                                 allow_agent=False)
            else:
                key = RSAKey.from_private_key_file('/home/redeyed/.ssh/id_rsa')
                self.ssh.connect(hostname=self.ip,
                                 username=self.login,
                                 pkey=key,
                                 look_for_keys=False)
            return True
        except:
            return False

    def disconect(self):
        self.ssh.close()

    def cmd(self, command):
        stdin, stdout, stderr = self.ssh.exec_command(command)
        result = list(map(lambda l: l.replace('\n', ''), stdout.readlines()))
        return result