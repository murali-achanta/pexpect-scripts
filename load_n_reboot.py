#!/usr/bin/env python
# author: Murali Achanta
import nxos_spawn as ns
import sys
import threading
import yaml

def delete_file(mgmt_ip, file_name):
    '''
    Delete a file using Linux prompt
    '''
    test1 = ns.nxos_spawn(mgmt_ip)
    with test1 as child:
        if child.is_in_vsh():
            child.exit_vsh()
        child.single_command('rm /bootflash/{}'.format(file_name))

def copy_file(mgmt_ip, scp_cmd, module_num):
    '''
    Copy a file using scp command
    '''
    test1 = ns.nxos_spawn(mgmt_ip, user='admin', password='murali123', name='mod{}'.format(module_num))
    with test1 as child:
        if not child.is_in_vsh():
            child.goto_vsh()
        status, data = child.scp_file(scp_cmd)
        print '{} --> module {} status {}'.format(mgmt_ip, module_num, status)

def reboot_switch(mgmt_ip, kickstart, isan):
    '''
    Reboot NXOS switch args: kickstart and isan images
    '''
    test1 = ns.nxos_spawn(mgmt_ip, user='admin', password='murali123')
    with test1 as child:
        status, data = child.reload()
        print status
        if child.is_at_boot_prompt():
            status, data = child.boot(kickstart, isan)
            print '{} --> {}'.format(mgmt_ip, status)

def copy_n_reload(mgmt_ip, kickstart_dst, isan_dst, kickstart_scp_cmd, isan_scp_cmd):
    '''
    Deletes old files using linux prompt and
    Copies new files from workspace and
    Reboots the switch with new files
    '''
    delete_file(mgmt_ip, kickstart_dst)
    delete_file(mgmt_ip, isan_dst)
    copy_file(mgmt_ip, kickstart_scp_cmd, 'sup')
    copy_file(mgmt_ip, isan_scp_cmd, 'sup')
    reboot_switch(mgmt_ip, kickstart_dst, isan_dst)

def do_for_all_switches(data):
    ''' 
    load and reboot all devices in the data
    this function uses threads to spawn multiple sessions
    '''
    threads = []
    for sw_name in data.keys():
        switch_data = data[sw_name]
        kickstart_cmd = switch_data['scp_cmd_template'] % (switch_data['ws_name'],
                                                           switch_data['kickstart'], 
                                                           switch_data['kickstart_dest'])
        isan_cmd = switch_data['scp_cmd_template'] % (switch_data['ws_name'],
                                                      switch_data['isan'],
                                                      switch_data['isan_dest'])
        t = threading.Thread(target=copy_n_reload, args=(switch_data['console'], 
                                                         switch_data['kickstart_dest'], 
                                                         switch_data['isan_dest'], 
                                                         kickstart_cmd, 
                                                         isan_cmd,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

if __name__ == '__main__':
    switches_data_file='switches.yml'
    if len(sys.argv) <= 1:
        print ">>>> usage: {} switch name from {} <<<<".format(sys.argv[0],switches_data_file)
        exit()
    with open(switches_data_file, 'r') as s:
        data = yaml.safe_load(s)
    switch = sys.argv[1]
    switch_data = data[switch]
    kickstart_cmd = switch_data['scp_cmd_template'] % (switch_data['ws_name'],
                                                       switch_data['kickstart'], 
                                                       switch_data['kickstart_dest'])
    isan_cmd = switch_data['scp_cmd_template'] % (switch_data['ws_name'],
                                                  switch_data['isan'],
                                                  switch_data['isan_dest'])
    copy_n_reload(switch_data['console'], 
                  switch_data['kickstart_dest'], 
                  switch_data['isan_dest'],
                  kickstart_cmd,
                  isan_cmd)
