"""FOSS-BU Arena desktop launcher. Windows executable / Linux Python source."""
import hashlib, ipaddress, os, socket, subprocess, sys, threading, time, zipfile
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

APP_NAME = 'FOSS-BU Arena'
VERSION = '1.0.0'
PLATFORM = 'windows' if sys.platform == 'win32' else 'linux'
RESOURCE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
PAYLOAD = RESOURCE / 'payload.zip'
COLOR = {'bg':'#0b1820','panel':'#122630','text':'#eef8f4','muted':'#a9c5bf','accent':'#79e8d0','button':'#225b5a'}
REQUIRED = ['freedm.wad','FOSSBU-Arena-v2.pk3','FOSSBU-Zombies.pk3','zandronum.pk3'] + (['zandronum.exe','fmodex64.dll'] if PLATFORM == 'windows' else ['zandronum','zandronum-server','libfmodex64-4.44.64.so'])

def install_path():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) if PLATFORM == 'windows' else Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    return base/'FOSS-BU Arena'/(VERSION+'-'+PLATFORM)

def install():
    if not PAYLOAD.is_file(): raise RuntimeError('The game package is missing. Keep all files together.')
    dest = install_path(); dest.mkdir(parents=True,exist_ok=True)
    # Do not overwrite settings or other files: extract only known package files, with an integrity check.
    with zipfile.ZipFile(PAYLOAD) as z:
        bad = z.testzip()
        if bad: raise RuntimeError('Game package is damaged: '+bad)
        for item in z.infolist():
            name = item.filename
            if not name or '/' in name or '\\' in name or name in ('.','..'): raise RuntimeError('Unexpected file in game package.')
            target = dest/name
            expected = hashlib.sha256(z.read(item)).digest()
            if not target.is_file() or hashlib.sha256(target.read_bytes()).digest() != expected:
                tmp = dest/(name+'.installing')
                with z.open(item) as src, tmp.open('wb') as out:
                    while block := src.read(1024*1024): out.write(block)
                os.replace(tmp,target)
            if PLATFORM == 'linux' and name in ('zandronum','zandronum-server'): target.chmod(0o755)
    for name in REQUIRED:
        if not (dest/name).is_file(): raise RuntimeError('Missing game file: '+name)
    return dest

def host_address():
    # Prefer a physical Wi-Fi adapter so that a VPN address is not suggested.
    try:
        if PLATFORM == 'windows':
            cmd = "$c=Get-NetIPConfiguration | Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' -and $_.NetAdapter.HardwareInterface -eq $true }; $c | Sort-Object @{Expression={ if($_.InterfaceAlias -match 'Wi-Fi|Wireless|WLAN') {0} else {1} }} | Select-Object -First 1 -ExpandProperty IPv4Address | Select-Object -First 1 -ExpandProperty IPAddress"
            value=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).strip()
            if value: return str(ipaddress.IPv4Address(value))
        else:
            lines=subprocess.check_output(['ip','-o','-4','addr','show','up'],text=True,timeout=5).splitlines()
            choices=[]
            for line in lines:
                parts=line.split(); name=parts[1].split('@')[0]; address=parts[3].split('/')[0]
                if name!='lo' and not name.startswith(('tun','tap','wg','docker','veth')): choices.append((0 if name.startswith(('wl','wlan')) else 1,address))
            if choices: return sorted(choices)[0][1]
    except (OSError,ValueError,subprocess.SubprocessError): pass
    return ''

def check_free_port():
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        if PLATFORM=='windows' and hasattr(socket,'SO_EXCLUSIVEADDRUSE'): sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        sock.bind(('',10666));return True
    except OSError: return False
    finally: sock.close()

def game_args(zombies):
    result=['-iwad','freedm.wad','-file','FOSSBU-Arena-v2.pk3']
    if zombies: result.append('FOSSBU-Zombies.pk3')
    return result

class Launcher:
    def __init__(self,root):
        self.root=root; self.directory=None; self.server=None; self.mode=tk.StringVar(value='Classic 1v1'); self.address=tk.StringVar(value=''); self.friend=tk.StringVar(); self.state=tk.StringVar(value='Preparing game files...')
        root.title(APP_NAME);root.configure(bg=COLOR['bg']);root.minsize(700,610)
        root.option_add('*Font',('Segoe UI',10));root.protocol('WM_DELETE_WINDOW',self.close)
        frame=tk.Frame(root,bg=COLOR['bg'],padx=30,pady=22);frame.pack(fill='both',expand=True)
        def label(text,size=10,color='text',bold=False):
            return tk.Label(frame,text=text,bg=COLOR['bg'],fg=COLOR[color],font=('Segoe UI',size,'bold' if bold else 'normal'),anchor='w',justify='left')
        label('FOSS-BU  /  ARENA',23,'accent',True).pack(fill='x')
        label('LOCAL MULTIPLAYER',9,'muted',True).pack(fill='x',pady=(2,15))
        label('Choose your match',14,'text',True).pack(fill='x')
        label('Both players must choose the same mode and use this version.',10,'muted').pack(fill='x',pady=(2,7))
        modes=tk.Frame(frame,bg=COLOR['bg']);modes.pack(fill='x')
        for title in ('Classic 1v1','1v1 + zombies'):
            tk.Radiobutton(modes,text=title,variable=self.mode,value=title,bg=COLOR['bg'],fg=COLOR['text'],activebackground=COLOR['bg'],activeforeground=COLOR['text'],selectcolor=COLOR['panel'],font=('Segoe UI',10)).pack(side='left',padx=(0,20))
        label('HOST A MATCH',10,'accent',True).pack(fill='x',pady=(19,5))
        label('Your network address: use your Wi-Fi IPv4 if a VPN is active.',10,'muted').pack(fill='x')
        row=tk.Frame(frame,bg=COLOR['bg']);row.pack(fill='x',pady=7)
        tk.Entry(row,textvariable=self.address,bg=COLOR['panel'],fg=COLOR['text'],insertbackground='white',relief='flat',font=('Consolas',13),width=25).pack(side='left',ipady=7,fill='x',expand=True)
        self.button(row,'Copy',self.copy,side='left',padx=(10,0))
        self.hostbtn=self.button(frame,'Host match',self.host,fill='x',pady=(0,4))
        self.stopbtn=self.button(frame,'Stop my server',self.stop,fill='x');self.stopbtn.config(state='disabled')
        label('JOIN A MATCH',10,'accent',True).pack(fill='x',pady=(19,5))
        label('Enter the host’s Wi-Fi IPv4 address:',10,'muted').pack(fill='x')
        row=tk.Frame(frame,bg=COLOR['bg']);row.pack(fill='x',pady=7)
        tk.Entry(row,textvariable=self.friend,bg=COLOR['panel'],fg=COLOR['text'],insertbackground='white',relief='flat',font=('Consolas',13)).pack(side='left',ipady=7,fill='x',expand=True)
        self.joinbtn=self.button(row,'Join',self.join,side='left',padx=(10,0))
        label('Same Wi-Fi • UDP 10666 • 20 frags or 10 minutes',9,'muted').pack(fill='x',pady=(15,2))
        tk.Label(frame,textvariable=self.state,bg=COLOR['bg'],fg=COLOR['accent'],wraplength=630,anchor='w',justify='left').pack(fill='x',pady=(6,3))
        label('FreeDM + Zandronum • FMOD by Firelight Technologies Pty Ltd.',8,'muted').pack(side='bottom',fill='x')
        self.hostbtn.config(state='disabled');self.joinbtn.config(state='disabled')
        threading.Thread(target=self.prepare,daemon=True).start()
    def button(self,parent,text,cmd,**opts):
        b=tk.Button(parent,text=text,command=cmd,bg=COLOR['button'],fg='white',activebackground='#307b76',activeforeground='white',relief='flat',padx=18,pady=8,font=('Segoe UI',10,'bold'));b.pack(**opts);return b
    def prepare(self):
        try:
            if PLATFORM=='linux' and os.uname().machine not in ('x86_64','amd64'): raise RuntimeError('This Linux package requires an x86-64 PC. Raspberry Pi ARM is not supported by this build.')
            directory=install();address=host_address();self.root.after(0,lambda:self.ready(directory,address))
        except Exception as exc:
            msg=str(exc);self.root.after(0,lambda:self.fail('Could not prepare the game',msg))
    def ready(self,directory,address): self.directory=directory;self.address.set(address);self.hostbtn.config(state='normal');self.joinbtn.config(state='normal');self.state.set('Ready. Connect both computers to the same Wi-Fi.' if address else 'Ready. Find your Wi-Fi IPv4 address in network settings.')
    def fail(self,title,msg): self.state.set(title+': '+msg);messagebox.showerror(title,msg)
    def copy(self):
        if self.address.get():self.root.clipboard_clear();self.root.clipboard_append(self.address.get());self.state.set('Address copied. Share it with your friend.')
    def run(self,server,args):
        name=('zandronum.exe' if PLATFORM=='windows' else ('zandronum-server' if server else 'zandronum'))
        env=os.environ.copy()
        if PLATFORM=='linux': env['LD_LIBRARY_PATH']=str(self.directory)+os.pathsep+env.get('LD_LIBRARY_PATH','')
        return subprocess.Popen([str(self.directory/name)]+args,cwd=self.directory,env=env)
    def host(self):
        if not check_free_port(): self.fail('Cannot host','UDP port 10666 is already in use. Close the other server and try again.');return
        zombies=self.mode.get()=='1v1 + zombies'
        args=['-host','-port','10666']+game_args(zombies)+['+deathmatch','1','+sv_nomonsters',('0' if zombies else '1'),'+sv_monsterrespawn',('1' if zombies else '0'),'+sv_maxplayers','2','+sv_maxclients','2','+sv_updatemaster','0','+fraglimit','20','+timelimit','10','+map','map01']
        try: self.server=self.run(True,args)
        except OSError as exc: self.fail('Server did not start',str(exc));return
        self.hostbtn.config(state='disabled');self.stopbtn.config(state='normal');self.state.set('Starting server. Keep this launcher and the server open...')
        self.root.after(6000,lambda:self.host_ready(zombies))
    def host_ready(self,zombies):
        if self.server is None:return
        if self.server.poll() is not None: self.hostbtn.config(state='normal');self.stopbtn.config(state='disabled');self.state.set('Server closed during startup. Check your system or try again.');return
        try:self.run(False,game_args(zombies)+['-connect','127.0.0.1:10666'])
        except OSError as exc:self.fail('Game did not start',str(exc));return
        self.state.set('Server started. Share your Wi-Fi address and selected mode.')
    def join(self):
        try: ip=str(ipaddress.IPv4Address(self.friend.get().strip()))
        except ValueError:self.fail('Invalid address','Enter the host’s IPv4 address, for example 192.168.1.10.');return
        try:self.run(False,game_args(self.mode.get()=='1v1 + zombies')+['-connect',ip+':10666']);self.state.set('Connecting. The host must use the same mode and version.')
        except OSError as exc:self.fail('Game did not start',str(exc))
    def stop(self):
        if self.server and self.server.poll() is None:self.server.terminate()
        self.server=None;self.hostbtn.config(state='normal');self.stopbtn.config(state='disabled');self.state.set('Server stopped. Close the game window separately.')
    def close(self):
        if self.server and self.server.poll() is None and not messagebox.askyesno('Server running','Stop the server and close the launcher?'):return
        if self.server and self.server.poll() is None:self.server.terminate()
        self.root.destroy()

def main():
    if '--self-test' in sys.argv:
        d=install(); print('Payload verified and extracted:',d);return
    root=tk.Tk(); app=Launcher(root);root.mainloop()
if __name__=='__main__':main()

