#!/usr/bin/env python
# author: Murali Achanta
import pexpect
import sys
import re
import time
import os

class nxos_spawn(object):
    '''
    context manager class for managing nxos switch 
    from pexpect.spawn()
    can be used with 'with' statememnt:
     ' import nxos_spawn as ns
        with ns.nxos_spawn('192.168.1.1', password='murali123') as child:
          print child.single_command('show module | no-more')
     '
    logfile_read will be under ./nxos_spawn_log directory
    '''
    def __init__(self, mgmt_ip, user='admin', password=None, name=None):
        self.c = None
        self.user=user
        self.mgmt_ip = mgmt_ip
        self.password = password
        self.switch_prompt = '#'
        self.loader_prompt = 'loader>'
        if name is None:
            self.name='%d' %(id(self))
        else:
            self.name=name
    def __enter__(self):
        self.c = pexpect.spawn('telnet  %s' % (self.mgmt_ip), timeout=120)
        self.c.logfile_name = 'nxos_spawn_log/log_%s_%s_%s.log' %(self.name, time.time(),self.mgmt_ip)
        directory = os.path.dirname(self.c.logfile_name)
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.c.logfile_read = open(self.c.logfile_name, 'a')
        time.sleep(1)
        self.c.sendline('')
        index = self.c.expect(['.*Connection refused.*',
                               '.*login:',
                               'Pass.*?:',
                               self.switch_prompt,
                               self.loader_prompt,
                               pexpect.TIMEOUT], timeout=30)
        if index == 0:
            raise RuntimeError('Connection refused')
        if index == 5:
            raise RuntimeError('timeout')
        if index == 1:
            self.c.sendline(self.user)
            self.c.expect('Pass.*?:', timeout=120)
        if index == 1 or index == 2:
            if self.password is not None:
                self.c.sendline(self.password)
            else:
                self.c.sendline('')
            self.c.expect(self.switch_prompt)
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.c.logfile_read.close()
        self.c.terminate()
    def __del__(self):
        pass
    def _send_yes(self):
        self.c.sendline('yes')
    def _send_y(self):
        self.c.sendline('y')
    def _send_n(self):
        self.c.sendline('n')
    def _send_no(self):
        self.c.sendline('no')
    def set_switch_prompts(self, prompt, loader_prompt):
        '''
        set switch prompt and loader prompt to look for
        '''
        self.switch_prompt = prompt
        self.loader_prompt = loader_prompt
    def single_command(self, command, at_loader=False):
        '''
        runs a single command returns the output
          to run command at loader prompt pass at_loader=True
        '''
        self.c.before = ''
        if at_loader:
            p = self.loader_prompt
        else:
            p = self.switch_prompt
        self.c.sendline(command)
        self.c.expect(p, timeout=120)
        return self.c.before
    def goto_vsh(self):
        '''
        issues 'vsh' command to enter vsh shell 
        useful when spawned task is at linux prompt
        '''
        self.c.sendline('vsh')
        self.c.expect(self.switch_prompt, timeout=120)
        self.c.sendline('term len 0')
        self.c.expect(self.switch_prompt)
        self.c.sendline('term width 100')
        self.c.expect(self.switch_prompt)
    def exit_vsh(self):
        '''
        issues 'exit' command to return to linux prompt
        '''
        self.c.sendline('exit')
        self.c.expect(self.switch_prompt)
    def is_in_vsh(self):
        '''
        checks if the task is in VSH prompt or linux prompt
        by running 'show clock' command
        retuns True, False or None(incase of timeout)
        '''
        self.c.sendline('show clock')
        index = self.c.expect(['Time.*',
                               '.*command not found.*',
                               pexpect.TIMEOUT], timeout=1)
        if index == 1:
            return False
        if index == 0:
            return True
        return None
    def is_at_boot_prompt(self):
        '''
        checks if the task is at boot prompt
        by sending '' command
        retuns True, False or None(incase of timeout)
        '''
        self.c.sendline('')
        index = self.c.expect([self.loader_prompt,
                               self.switch_prompt,
                               pexpect.TIMEOUT], timeout=1)
        if index == 1:
            return False
        if index == 0:
            return True
        return None
    def reload_lc(self, module_num):
        '''
          reload module using nxos reload module cli
          and responds to reload prompt
          child needs to be at vsh prompt before calling
          retuns tuple (synopsis =['reloaded','timedout'] , data)
        '''
        synopsis = ''
        self.c.before = ''
        reload_cmd = 'reload module {} force-dnld'.format(module_num)
        self.c.sendline(reload_cmd)
        index = self.c.expect(['Proceed[y/n]?',
                               pexpect.TIMEOUT], timeout=120)
        if index == 0:
            self.c.sendline('y')
            synopsis='reloaded'
            self.c.expect(self.switch_prompt)
        elif index == 1:
            synopsis = 'timedout'
        data = self.c.before
        return synopsis, data
    def reload(self):
        '''
          reload switch and bring it to boot prompt
          child needs to be at vsh prompt before calling
          retuns tuple (synopsis =['reloaded','timedout'] , data)
        '''
        synopsis = ''
        self.c.before = ''
        self.c.sendline('reload')
        index = self.c.expect(['This command will reboot the system. (y/n)?.*',
                               pexpect.TIMEOUT], timeout=120)
        if index == 0:
            self.c.sendline('y')
            self.c.sendline('')
            synopsis='reloaded'
            self.c.expect(self.loader_prompt, timeout=120)
        elif index == 1:
            synopsis = 'timedout'
        data = self.c.before
        return synopsis, data
    def boot(self, kickstart, isan, password):
        '''
        boot switch with kickstart and isan
        '''
        synopsis = ''
        self.c.before = ''
        if not self.is_at_boot_prompt():
            synopsis = 'not at boot prompt'
            return synopsis, ''
        self.c.sendline('boot {} {}'.format(kickstart, isan))
        def _send_admin_pass():
            self.c.sendline(str(password))
        '''
        p_tuple is a list of pattern tupple,
         each tuple has ('pattern to expect', 'synopsis', action_fn)
        '''
        s = []
        p_tuple = [(pexpect.TIMEOUT,
                    'timed out', 'return'),
                   ('System image digital signature verification fail',
                    'signature failed', 'return'),
                   (self.loader_prompt,
                    'back to loader prompt',
                    'return'),
                   ('Abort Auto Provisioning and continue with normal setup.*:',
                    'auto provision',
                    self._send_y),
                   ('Do you want to enforce secure password standard.*:',
                    'enforce password',
                    self._send_y),
                   ('Enter the password for "admin":',
                    'set admin pass',
                    _send_admin_pass),
                   ('Confirm the password for "admin":',
                    'set admin pass',
                    _send_admin_pass),
                   ('Do you want to enable admin vdc.*:',
                    'enable admin vdc ',
                    self._send_n),
                   ('Would you like to enter the basic configuration dialog.*:',
                    'basic config dialog',
                    self._send_no),
                   ('.*login:',
                    'at login prompt',
                    'break'),
                   ('#',
                    'at kickstart prompt',
                    'return')]
        p_list = [p[0] for p in p_tuple]
        while True:
            index = self.c.expect(p_list, timeout=1200)
            s.append(p_tuple[index][1])
            if p_tuple[index][2] == 'return':
                data = self.c.before
                return s, data
            if p_tuple[index][2] == 'break':
                break
            p_tuple[index][2]()
        data = self.c.before
        return s, data
    def scp_file(self, command, password=None):
        '''
        scp file from vsh prompt, expects child in vsh prompt
        command argument must have complete scp command
        returns tuple (synopsis = ['Permission deined',
                            'command timed out',
                            'copy failed',
                            'copy completed',
                            'No such file or directory'],
                       data)
        '''
        if password is None:
            password = 'abc123'
        self.c.before = ''
        self.c.sendline('term len 0')         # turn-off "more" paging
        self.c.expect(self.switch_prompt)
        self.c.sendline('term width 100')     # turn-off line wrapping
        self.c.expect(self.switch_prompt)
        self.c.sendline(command)
        '''
        p_tuple is a list of pattern tupple,
         each tuple has ('pattern to expect', 'synopsis', action_fn)
        '''
        p_tuple = [(pexpect.TIMEOUT,
                    'command timed out', 'return'),
                  ('Permission denied.*Cannot overwrite existing file',
                   'permission deined', 'return'),
                  ('Overwriting/deleting this image is not allowed',
                   'overwrite not allowed',
                   'return'),
                  ('Are you sure you want to continue connecting (yes/no)?',
                   'scp connecting prompt', self._send_yes),
                  ('Do you want to overwrite (y/n)?',
                   'overwrite prompt', self._send_y),
                  ('[Pp]ass.*?:',
                   'password prompt', 'break')]
        p_list = [p[0] for p in p_tuple]
        while True:
            index = self.c.expect(p_list, timeout=120)
            if p_tuple[index][2] == 'return':
                data = self.c.before
                return p_tuple[index][1], data
            if p_tuple[index][2] == 'break':
                break
            p_tuple[index][2]()
        self.c.sendline(password)
        p_tuple = [(pexpect.TIMEOUT,
                   'copy timed out'),
                  ('Copy complete.*', 
                   'copy completed'),
                  ('Copy failed.*',
                   'copy failed'),
                  ('No such file or directory',
                   'file not found')]
        index = self.c.expect([p[0] for p in p_tuple],
                              timeout=600)
        data = self.c.before
        return p_tuple[index][1], data
