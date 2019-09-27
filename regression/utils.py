import paramiko

class SSH:
    def __init__(self, host, username, password, port=22, sftp=True, timeout=None, environment={}):
        self.timeout = timeout
        self.environment = environment
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, username=username, password=password, port=port)
        self.sftp = self.client.open_sftp() if sftp else None
    
    def execute(self, command, wait=True):
        stdin, stdout, stderr = self.client.exec_command('; '.join(command) if isinstance(command, list) else command, timeout=self.timeout) # environment=self.environment
        channel = stdout.channel
        if wait:
            status_code = channel.recv_exit_status()
        else:
            status_code = 0
        return stdin, stdout, stderr, channel, status_code
    
    def get_file(self, path, mode='r'):
        return self.sftp.file(path, mode=mode) if self.sftp else None
    
    def put_file(self, local_path, remote_path):
        return self.sftp.put(local_path, remote_path) if self.sftp else None
    
    def close(self):
        if self.sftp:
            self.sftp.close()
        self.client.close()
