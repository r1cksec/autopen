# Autopen

Autopen is a very modular tool that automates the execution of scans during a penetration test.
A Nmap scan result in the form of an XML file is required as the basis for the modules to be executed.
This XML file can be passed as an argument.
If no scan result is provided, autopen can perform the Nmap scan by itself.
<br>
<br>
Using multithreading, several scans are executed simultaneously.
The use of different modules can be adapted on the fly by using module names, port numbers or IP addresses as a filter.
Autopen is well suited to test a given user password combination on many machines and different services.
<br>
<br>
The core is the `modules.json` file, which contains the syntax of the executable commands.
Variables can also be stored in this configuration file, which are automatically included in the arguments of Argparse.

## Requirements
- Python 3

Furthermore all modules specified in the configuration file are considered as dependencies. <br>
If a module is not installed, an error is issued and the next module is executed.

## Install
The setup script will only read the absolute path of the script location and insert this path into the `modules.json` file.

```
bash setup.sh
```

## Configuration
The `modules.json` file contains all modules that can be executed by autopen. <br>
The modules have the following structure:

```
{
    "name": "nameOfModule",
    "riskLevel": "riskLevelAsInteger",
    "syntax": "commandSyntax <targetIp> [optional <variable>] > <outputFile> 2>&1",
    "port": "portNumber1, portNumber2, [...]"
},
```

### name, risklevel, port
The configuration can be extended as desired. <br>
However, it should be noted that the modules cannot have the same name.
<br>
<br>
Each module requires a risk level between 1 to 4.  <br>
The higher the level, the higher the probability that the module can cause damage.
<br>
<br>
It is necessary to specify port numbers for the modules. <br>
If a module is always applicable, a wildcard `*` can also be stored instead a port number. <br>
In this case, the module will be executed once for each host and each port.

```
{
    "name": "crackmapexec",
    "riskLevel": "1",
    "syntax": "crackmapexec smb <targetIp> > <outputFile> 2>&1",
    "port": "445"
},
{
    "name": "netcat",
    "riskLevel": "1",
    "syntax": "timeout 60 nc -nv <targetIp> <port> > <outputFile> 2>&1",
    "port": "*"
},

```

### syntax - absolute path
If tools are not included in the environment path variables, absolute paths can also be specified. 

```
{
    "name": "lsassy",
    "riskLevel": "2",
    "syntax": "/usr/bin/lsassy -d <domain> -u <user> -p <password> <targetIp> > <outputFile> 2>&1",
    "port": "445"
},
```

### syntax - variables
Strings inside `<...>` are interpreted as variables. <br>
The syntax must always end with an `> <outputFile> 2>&1` so that the output can be written to a file. <br>
Additionally the `<targetIp>` variable must always be included inside the syntax.
<br>
<br>
Furthermore it is possible to include custom variables.
Custom variables are added to the arguments of Argparse.
Camelcase notation sets the abbreviations for the Argparse's arguments.
<br>
<br>
Modules with custom variables are only executed if all `<variables>` occurring in the syntax are given by the user. <br>
One exceptional variable that does not have to be passed explicitly when autopen is called is the variable `<port>`.
This variable is read from the Nmap scan result. <br>
For example, the following module would add the values `domain (-d)` and `userList (-ul)` to the Argparse's arguments.

```    
{
    "name": "smtp-enum-user",
    "riskLevel": "1",
    "syntax": "smtp-user-enum -M VRFY -D <domain> -U <userList> -w 30 -v -t <targetIp> > <outputFile> 2>&1",
    "port":"25"
},
```

## Help
```
usage: autopen.py [-h] [-e] [-v] -o OUTPUT [-t TIMEOUT] (-ti TARGETIP | -xf XMLFILE) [-rl RISKLEVEL] [-ta THREADAMOUNT] [-em [EXCLUDEMODULES ...]] [-im [INCLUDEMODULES ...]] [-ii [INCLUDEIPS ...]]
                  [-ei [EXCLUDEIPS ...]] [-ip [INCLUDEPORTS ...]] [-ep [EXCLUDEPORTS ...]] [-d DOMAIN] [-dci DOMAINCONTROLERIP] [-p PASSWORD] [-u USER] [-ul USERLIST] [-upf USERPASSFILE]

Automatic Pentesting.
Please dont be evil.

Basic usage:
Print matching modules for a given nmap xml file:
./autopen.py -o /tmp/output -xf nmap-result.xml

Scan targets (top 1000 ports) and execute matching modules:
./autopen.py -o /tmp/output -ti 192.168.0.0/24 -e

Exclude ip addresses:
./autopen.py -o /tmp/output -xf nmap-result.xml -ei 192.168.1.1 192.168.3.4 -e

Only execute modules for given ip address and exclude ports:
./autopen.py -o /tmp/output -xf nmap-result.xml -ii 192.168.1.4 -ep 80 443 -e

Exclude all modules that have one of the given substrings in their name:
./autopen.py -o /tmp/output -xf nmap-result.xml -im smb netcat -e

Only execute modules that contains at least one given substring in ther name:
./autopen.py -o /tmp/output -xf nmap-result.xml -im hydra -e

Execute modules with higher risk level, use more threads and increase timeout:
./autopen.py -o /tmp/output -xf nmap-result.xml -rl 4 -ta 8 -t 900

optional arguments:
  -h, --help            show this help message and exit
  -e, --execute         execute matching commands
  -v, --verbose         print full command
  -o OUTPUT, --output OUTPUT
                        path to output directory
  -t TIMEOUT, --timeout TIMEOUT
                        maximal time that a single thread is allowed to run in seconds (default 600)
  -ti TARGETIP, --targetIp TARGETIP
                        initiate nmap scan for given ip addresses (use nmap ip address notation)
  -xf XMLFILE, --xmlFile XMLFILE
                        full path to xml nmap file
  -rl RISKLEVEL, --riskLevel RISKLEVEL
                        set maximal riskLevel for modules (possible values 1-4, 2 is default)
  -ta THREADAMOUNT, --threadAmount THREADAMOUNT
                        the amount of parallel running threads (default 5)
  -em [EXCLUDEMODULES ...], --exludeModules [EXCLUDEMODULES ...]
                        modules that will be excluded (exclude ovewrites include)
  -im [INCLUDEMODULES ...], --includeModules [INCLUDEMODULES ...]
                        modules that will be included
  -ii [INCLUDEIPS ...], --includeIps [INCLUDEIPS ...]
                        filter by including ipv4 addresses
  -ei [EXCLUDEIPS ...], --excludeIps [EXCLUDEIPS ...]
                        filter by excluding ipv4 addresses
  -ip [INCLUDEPORTS ...], --includePorts [INCLUDEPORTS ...]
                        filter by including port number
  -ep [EXCLUDEPORTS ...], --excludePorts [EXCLUDEPORTS ...]
                        filter by excluding port number
  -d DOMAIN, --domain DOMAIN
  -dci DOMAINCONTROLERIP, --domainControlerIp DOMAINCONTROLERIP
  -p PASSWORD, --password PASSWORD
  -u USER, --user USER
  -ul USERLIST, --userList USERLIST
  -upf USERPASSFILE, --userPassFile USERPASSFILE
```

## Demo
![](https://github.com/r1cksec/autopen/blob/master/demo.gif)

## Result Structure 
```
output
├── dirsearch
│   ├── dirsearch-192.168.2.175-80
│   └── dirsearch-192.168.2.175-8080
├── hydra-ftp-default-creds
│   └── hydra-ftp-default-creds-192.168.2.175-21
├── hydra-ssh-default-creds
│   └── hydra-ssh-default-creds-192.168.2.175-22
├── netcat
│   ├── netcat-192.168.2.175-21
│   ├── netcat-192.168.2.175-22
│   ├── netcat-192.168.2.175-80
│   └── netcat-192.168.2.175-8080
├── nmap
│   ├── 192.168.2.175-p-sT.gnmap
│   ├── 192.168.2.175-p-sT.nmap
│   └── 192.168.2.175-p-sT.xml
├── ssh-audit
│   └── ssh-audit-192.168.2.175-22
└── whatweb
    └── whatweb-192.168.2.175-80
```

## Currently included Modules

**Sources**

* <https://github.com/byt3bl33d3r/CrackMapExec>
* <https://github.com/CiscoCXSecurity/enum4linux>
* <https://github.com/diegocr/netcat>
* <https://github.com/Hackndo/lsassy>
* <https://github.com/jtesta/ssh-audit>
* <https://github.com/maurosoria/dirsearch>
* <https://github.com/nmap/nmap>
* <https://github.com/OJ/gobuster>
* <https://github.com/projectdiscovery/nuclei>
* <https://github.com/SecureAuthCorp/impacket/blob/master/examples/secretsdump.py>
* <https://github.com/ShawnDEvans/smbmap>
* <https://github.com/sullo/nikto>
* <https://github.com/urbanadventurer/WhatWeb>
* <https://github.com/vanhauser-thc/thc-hydra>
* <https://gitlab.com/kalilinux/packages/smtp-user-enum>
* <https://man.archlinux.org/man/rpcinfo.8.en>
* <https://man.archlinux.org/man/showmount.8.en>

