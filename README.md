#pexpect scripts for cisco nexus os 

These are some python scripts with context manager to make further automation of daily tasks a little pythonic for nxos switch. It has system reload and scp prompt handling.

eg:

```python
>>> with ns.nxos_spawn('192.168.1.1',user='admin',password='1234', name='sw1') as child:
...   print child.single_command('show version | no-more')                                                                                            
... 
>>>
```