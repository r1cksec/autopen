from argparse import RawTextHelpFormatter
import argparse
import json
import os
import signal
import subprocess
import threading
import time
import xml.etree.ElementTree as ET


"""Load JSON content of module configuration file.

pathToModuleConfig = The path to the configuration file.
"""
def loadModules(pathToModuleConfig):
    with open(pathToModuleConfig, "r", encoding="utf-8") as file:
        return json.load(file)


"""Return a list of strings.
Each string in this list represents a <variable> of the syntax string.
These syntax strings are read from the modules.json file.
Furthermore it is possible to skip exceptional strings.
This exceptional strings: 'outputFile', 'port', 'targetIp', 'xmlFile'
will not be added to the list of strings.

syntax = The syntax of the command of the given module.
removeExpArgs = If this value is set to 1, it will be checked 
whether string belongs to the exceptional strings.
"""
def getVariablesFromString(syntax, removeExpArgs):
    possRequiredVars = []
    splittedSyntax = syntax.split("<")
    
    for currSpl in splittedSyntax:
        if (">" in currSpl):
            variableOfTempl = currSpl.split(">")
            possRequiredVars.append(variableOfTempl[0])
    
    # get all undefined variables inside json config of modules
    requiredVars = []
    
    # add if json key for module does not exist
    for var in possRequiredVars:
        try:
            # check if json key exists 
            if (currModule[var]):
                continue
        except:
            requiredVars.append(var)

    if (removeExpArgs == 1):
        # define exceptional arguments 
        exceptionalArguments = ["outputFile", "port", "targetIp", "xmlFile"]
        
        # remove exceptional variables from json arguments
        for currExceptArg in exceptionalArguments:
            if (currExceptArg in requiredVars): 
                requiredVars.remove(currExceptArg)

    return requiredVars


"""Return a list of strings that will be added to argumentParser.
These strings are defined in the modules.json file within the syntax key.
For each module, the values set in <variable> are defined as arguments.
Exceptional arguments like:
'outputFile', 'port', 'targetIp', 'xmlFile'
will not be added to the argumentParser.
"""
def getArgsOfJson():
    availableModules = loadModules(pathToScriptDir + "/modules.json")

    # define arguments given by json config
    allJsonArgs = []
    
    for currModule in availableModules:
        allRequiredVars = getVariablesFromString(currModule["syntax"], 1)
    
        for currArg in allRequiredVars:
            allJsonArgs.append(currArg)
    
    # remove duplicated undefined variables
    uniqJsonArgs = sorted(set(allJsonArgs))
 
    return uniqJsonArgs


"""Catch user interrupt (ctrl + c).

sig = The type of signal, that should be catched.
frame = The function that should be executed.
"""
def signal_handler(sig, frame):
    print ("\nCatched keyboard interrupt, exit programm!")

    try:
        print ("Remove empty directories and files before leaving...")
        if (args.execute):
            # remove empty directories
            for directory in os.scandir(args.output):
                if os.path.isdir(directory) and not os.listdir(directory):
                    os.rmdir(directory)

        # remove all temporary files
        for tmpFile in allTempFiles:
            os.remove(tmpFile)

        print("Done")
        exit(0)

    except:
        exit(0)


"""Return a list with following structure:
[["ip1","port80","port443"],["ip2","port22","port80"]]
This list is created from an XML nmap scan result.

pathToNmapXml = The full path to the current nmap xml result file.
"""
def convertXmlToList(pathToNmapXml):
    # read XML file into 2 dimensional list
    nmapAsList = []
 
    tree = ET.parse(pathToNmapXml)
    xmlRoot = tree.getroot()
 
    # get hosts
    for currentHost in xmlRoot.findall("./host"):
        # flush all buffers
        currentIpv4 = ""
        allOpenPortsOfCurrentIp = ""
 
        for currentAddress in currentHost.findall("address"):
            # ipv4 needs to stay highest node
            currentIpv4 = currentAddress.get("addr")
            break
 
        # check if ports are iterable
        if (currentHost.find("ports")):
            for extraPortsOrPort in currentHost.find("ports"):
                currentPortId = extraPortsOrPort.get("portid")
 
                for state in extraPortsOrPort.findall("state"):
                    state = state.get("state")
 
                    # check if current port is open
                    if (state == "open"):
                        allOpenPortsOfCurrentIp = allOpenPortsOfCurrentIp  \
                                                  + currentPortId + ","
 
        # remove last char (,) from all open ports of current ipv4
        allOpenPortsOfCurrentIp = allOpenPortsOfCurrentIp[:-1]
 
        # add ip and all its open ports to nmap as list
        nmapAsList.append([currentIpv4,allOpenPortsOfCurrentIp]) 
    
    return nmapAsList


"""Create a temporary file 
that contains all hosts of the nmap scan that matches a specific port number.
One host per line.

portnumbers = The port number that should be matched.
"""
def getAllTargetableHosts(portnumber):

    for currPossTarget in nmapIpPortList:
        filePointer = open(tempFileNameTemplate + portnumber, "a")
        # only scan IP addresses included by user
        if (args.includeIps != "NULL"):
            if (not currPossTarget[0] in args.includeIps):
                continue

        # skip ip addresses excluded by user
        if (args.excludeIps != "NULL"):
            if (currPossTarget[0] in args.excludeIps):
                continue

        # get every open port of current possible target host
        splittedOpenPortsOnHost = currPossTarget[1].split(",")
 
        for currentOpenPortOnHost in splittedOpenPortsOnHost:
            # skip empty splitted port lists
            if (currentOpenPortOnHost == ""):
                continue

            # write current host to file if ports are matching
            if (currentOpenPortOnHost == portnumber):
                # prevent duplicate ip addresses inside file of targetable hosts
                filePointer2 = open(tempFileNameTemplate + portnumber, "r")
                allLines = filePointer2.readlines()

                if (not currPossTarget[0] + "\n" in allLines):
                    filePointer.write(currPossTarget[0] + "\n")

                filePointer2.close()
                break

        filePointer.close() 



"""Return a list with all open portnumbers.
These ports are read from the nmap list.
"""
def getAllOpenPorts():
    allPorts = []

    for ipv4Addr in nmapIpPortList:
        # collect all ports of every single host
        splitPort = ipv4Addr[1].split(",")

        for portNum in splitPort:
            allPorts.append(portNum)

    uniqPorts = sorted(set(allPorts))
    return uniqPorts


"""Return a json object 
that contains modules which matches the arguments given by the user.
Furthermore this modules matches the open port numbers 
of current nmap scan result.
"""
def getMatchingModules():
    # read all modules from json file
    allModules = loadModules(pathToScriptDir + "/modules.json")
    matchingModules = []

    for module in allModules:
        # flag used to skip the current module
        skipModule = "0"
 
        # skip excluded modules given by user
        if (args.excludeModules != "NULL"):
            for currExcludedMod in args.excludeModules:
                if (currExcludedMod in module["name"]):
                    skipModule = "1"
                    break 
 
            if (skipModule == "1"):
                continue
 
        # only execute included modules given by user
        skipModule = "1"
 
        if (args.includeModules != "NULL"):
            for currIncludedMod in args.includeModules:
                if (currIncludedMod in module["name"]):
                    skipModule = "0"
                    break 
 
            if (skipModule == "1"):
                continue
 
        # get all undefined arguments of current module
        requiredArgsOfModule = getVariablesFromString(module["syntax"], 1)
        skipModule = "0"
 
        # skip modules that need an argument, that has not been given by user
        for currUndefArg in requiredArgsOfModule:
            if (vars(args)[currUndefArg] == "NULL"):
                skipModule = "1"
                break
 
        # execute only modules with lower equals risk level given by user
        if (int(module["riskLevel"]) > int(args.riskLevel)):
            skipModule = "1"
 
        if (skipModule == "1"):
            continue
        else:
            # check if module uses wildcard as portnumber
            if (module["port"] == "*"):
                allPortsAsString = ""
                overallPort = getAllOpenPorts()

                for port in overallPort:
                    allPortsAsString = allPortsAsString + "," + port

                # remove leading ,
                module["port"] = allPortsAsString[1:]

            # check if ports of current module matches nmap scan
            portsOfCurrentModule = module["port"].split(",")

            for currModPort in portsOfCurrentModule:
                # only scan ports included by user
                if (args.includePorts != "NULL"):
                    if (not currModPort in args.includePorts):
                        continue

                # skip ports excluded by user
                elif (args.excludePorts!= "NULL"):
                    if (currModPort in args.excludePorts):
                        continue

                pathToTempFileCurrPort = tempFileNameTemplate + currModPort

                # get list of hosts that can be targeted by current module
                # for a given port
                if (not os.path.exists(pathToTempFileCurrPort)):
                    getAllTargetableHosts(currModPort)
                    allTempFiles.append(pathToTempFileCurrPort)

                # skip module for current port 
                # if list of targetable host is empty
                if (os.stat(pathToTempFileCurrPort).st_size == 0):
                    continue
                else:
                    # set only the matching portnumber inside port key
                    # otherwise createCommandFromTemplate will not
                    # be able to get correct portnumber
                    module["port"] = currModPort

                    # append a copy of the module instead of a reference
                    matchingModules.append(module.copy())

    return matchingModules


"""Return a list of lists.
These lists contain all final commands that will be executed.
Commands that have already been executed will not be executed again.
This function will fill the syntax key of the modules.json file accordingly.

allExecutableModules = All modules that will be executed.
"""
def createCommandFromTemplate(allExecutableModules):
    allCommands = []

    for thisModule in allExecutableModules:
        pathToModDir = args.output + "/" + thisModule["name"]

        # create directories for modules
        if (args.execute):
            if (not os.path.isdir(pathToModDir)):
                os.makedirs(pathToModDir)

        argumentsOfModule = getVariablesFromString(thisModule["syntax"], 0)

        with open(tempFileNameTemplate + thisModule["port"]) as targetHosts:
            for host in targetHosts:
                host = host.replace("\n","")

                # the command that will be appended to list of commands
                exeString = thisModule["syntax"]

                # add additional arguments given by to the output path
                modOutput = pathToModDir + "/" + thisModule["name"]

                for currArg in argumentsOfModule:
                    # skip <outputFile> and <outputDir>
                    if (currArg == "outputFile" or currArg == "outputDir"):
                        continue

                    # insert portnumber
                    elif (currArg == "port"):
                        modOutput = modOutput + "-" + thisModule["port"]
                        exeString = exeString.replace("<port>",
                                                      thisModule["port"])

                    elif (currArg == "targetIp"):
                        # insert ip address
                        modOutput = modOutput + "-" + host
                        exeString = exeString.replace("<targetIp>", host)
                        ipAddressCounter.append(host)

                    else:
                        # replace remaining arguments
                        exeString = exeString.replace("<" + currArg + ">", 
                                                      vars(args)[currArg])

                # insert outputFile
                exeString = exeString.replace("<outputFile>", modOutput)

                # check if tool has already been executed
                if (os.path.exists(modOutput)):
                    print(f"{bcolor.yellow}###[DUPLICATE]###\t{bcolor.ends} "
                          + thisModule["name"] + "-" + host + "-"
                          + thisModule["port"])
                else:
                    allCommands.append([exeString, thisModule["name"] + "-"
                                       + host + "-" + thisModule["port"]])

    return allCommands


"""Return exit status for executed command.
Create thread and execute given tool.

threading.Thread = The command that will be executed inside a shell.
moduleName = The name of the module 
that will be printed after successfull execution.
"""
class threadForModule(threading.Thread):
    def __init__(self, command, moduleName):
        threading.Thread.__init__(self)
        self.command = command
        self.moduleName = moduleName

    def run(self):
        # check if modules should only be printed
        if (args.execute):
            try:
                # run command in new shell and wait for termination
                subprocess.check_output(self.command, shell=True, 
                                        timeout=float(args.timeout))
                print(f"{bcolor.green}###[DONE]###\t{bcolor.ends} "
                      + self.moduleName)
                return(0)

            except subprocess.CalledProcessError as exc:
                # skip error code 124 
                # since timeout is necessary for the usage of netcat
                if (exc.returncode == 124):
                    print(f"{bcolor.green}###[DONE]###\t{bcolor.ends} "
                          + self.moduleName)
                    return(0)

                # skip error code of module ssh-audit
                if (exc.returncode == 3 and "ssh-audit" in self.command):
                    print(f"{bcolor.green}###[DONE]###\t{bcolor.ends} "
                          + self.moduleName)
                    return(0)

                else:
                    print(f"{bcolor.red}###[ERROR]###\t{bcolor.ends} " 
                      + self.command)
                    return(1)


"""MAIN

"""
# define and configure static arguments
argumentParser = argparse.ArgumentParser(description="""Automatic Pentesting.
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

Only execute modules that contains at least one given substring in their name:
./autopen.py -o /tmp/output -xf nmap-result.xml -im hydra -e

Execute modules with higher risk level, use more threads and increase timeout:
./autopen.py -o /tmp/output -xf nmap-result.xml -rl 4 -ta 8 -t 900

Special characters in passwords must be escaped.
""", formatter_class=RawTextHelpFormatter)

requiredArgs = argumentParser.add_mutually_exclusive_group(required=True)

argumentParser.add_argument("-e",
                            "--execute", 
                            dest = "execute",
                            help = "execute matching commands",
                            action = "store_true")

argumentParser.add_argument("-v",
                            "--verbose",
                            dest = "verbose",
                            help = "print full command",
                            action = "store_true")

argumentParser.add_argument("-o",
                            "--output",
                            dest = "output",
                            help = "path to output directory",
                            required = "true")

argumentParser.add_argument("-t",
                            "--timeout",
                            dest="timeout",
                            help = "maximal time that a single thread"
                                 + " is allowed to run"
                                 + " in seconds (default 600)",
                            default = "600")

requiredArgs.add_argument("-ti",
                            "--targetIp",
                            dest = "targetIp",
                            help = "initiate nmap scan for given ip addresses"
                                   + " (use nmap ip address notation)")

requiredArgs.add_argument("-xf",
                            "--xmlFile",
                            dest = "xmlFile",
                            help = "full path to xml nmap file")

argumentParser.add_argument("-rl",
                            "--riskLevel",
                            dest = "riskLevel",
                            help = "set maximal riskLevel for modules"
                                   + " (possible values 1-4, 2 is default)",
                            default = "2")

argumentParser.add_argument("-ta",
                            "--threadAmount",
                            dest = "threadAmount",
                            help = "the amount of parallel running threads"
                                   + " (default 5)",
                            default = "5")

argumentParser.add_argument("-em",
                            "--exludeModules",
                            dest = "excludeModules",
                            nargs = "*",
                            help = "modules that will be excluded "
                                   + "(exclude ovewrites include)",
                            default = "NULL")

argumentParser.add_argument("-im",
                            "--includeModules",
                            dest = "includeModules",
                            nargs = "*",
                            help = "modules that will be included",
                            default = "NULL")

argumentParser.add_argument("-ii",
                            "--includeIps",
                            dest = "includeIps", 
                            nargs = "*",
                            help = "filter by including ipv4 addresses",
                            default = "NULL")

argumentParser.add_argument("-ei",
                            "--excludeIps",
                            dest = "excludeIps", 
                            nargs = "*",
                            help = "filter by excluding ipv4 addresses",
                            default = "NULL")

argumentParser.add_argument("-ip",
                            "--includePorts", 
                            dest = "includePorts", 
                            nargs = "*",
                            help = "filter by including port number",
                            default = "NULL")

argumentParser.add_argument("-ep",
                            "--excludePorts",
                            dest = "excludePorts", 
                            nargs = "*",
                            help = "filter by excluding port number",
                            default = "NULL")

# get path to directory that contains the json config
pathToScript = os.path.realpath(__file__)
pathToScriptDir  = os.path.dirname(pathToScript)
argsFromJsonConf = getArgsOfJson()

# add arguments of json file to argumentParser
for currJsonArg in argsFromJsonConf:
    capitalLetters = currJsonArg[0]

    for char in currJsonArg:
        if (char.isupper()):
            capitalLetters = capitalLetters + char     
    try:
        argumentParser.add_argument("-" + capitalLetters.lower(),
                                    "--" + currJsonArg,
                                    dest=currJsonArg,
                                    default="NULL")
    except:
        print("Error in modules.json - "
              + "collision for config argument name (args): " + currJsonArg)
        print("Argparse conflicting option string: --"
              + currJsonArg + "/-" + capitalLetters)
        exit(1)

args = argumentParser.parse_args()

# catch ctrl + c
signal.signal(signal.SIGINT, signal_handler)

# define colors for printing to stdout
class bcolor:
    purple = '\033[95m'
    blue = '\033[94m'
    green = '\033[92m'
    yellow = "\033[1;33m"
    red = '\033[91m'
    ends= '\033[0m'

# counts the overall ip addresses that will be scanned
ipAddressCounter = []

# check if some xml input has been given by user
if (args.xmlFile != "NULL" and args.xmlFile):
    pathToNmap = args.xmlFile

    # convert xml nmap file to list
    nmapIpPortList = convertXmlToList(pathToNmap)

else:
    pathToNmap = args.output + "/nmap"

    # create directory for nmap
    if (not os.path.exists(pathToNmap)):
        os.makedirs(pathToNmap)

    nmapScan = "nmap -p- -sT --min-rate 600 -Pn -oA " + pathToNmap + "/" \
               + args.targetIp + "-p-sT " + args.targetIp

    pathToNmap = pathToNmap + "/" + args.targetIp + "-p-sT.xml"
    os.system(nmapScan)

    # convert xml nmap file to list
    nmapIpPortList = convertXmlToList(pathToNmap)

# used to collect all temporary files
allTempFiles = []

# create temporary filenames based on path to nmap scan
tempFileNameTemplate = pathToNmap.replace("/", "_")
tempFileNameTemplate = "/tmp/autoPen" + tempFileNameTemplate + "-"

# remove temporary files that wrongly already exists
os.system("rm " + tempFileNameTemplate + "* 2> /dev/null")

# get a list with modules that matches the arguments given by user
executableModules = getMatchingModules()

# create commands from template
commandsToExecute = createCommandFromTemplate(executableModules)

# will contain the running threads
threads = []

# count finished modules
amountOfExecModules = len(commandsToExecute)
counter = 1

for runCommand in commandsToExecute:
    # execute modules inside parallel threads
    if (args.execute):
        if (args.verbose):
            print(f"{bcolor.blue}###[START]###\t{bcolor.ends} "
                  + runCommand[0] + " - " + str(counter) 
                  + "/" + str(amountOfExecModules))
        else:
            print(f"{bcolor.blue}###[START]###\t{bcolor.ends} "
                  + runCommand[1] + " - " + str(counter) 
                  + "/" + str(amountOfExecModules))

        counter += 1

        while 1:
            # run 5 threads in parallel
            if (threading.active_count() < int(args.threadAmount)):
                currThread = threadForModule(runCommand[0], runCommand[1])
                threads.append(currThread)
                currThread.start()
                break

            else:
                time.sleep(3)
    
    else:
        if (args.verbose):
            print(runCommand[0])
        else:
            print(runCommand[1])

# wait for all modules to finish
for x in threads:
    x.join()

# print amount of modules for each ip addresses
print("")
print(f"{bcolor.purple}### Amount of Modules \
to execute per Host: ###{bcolor.ends}")

uniqIps = sorted(set(ipAddressCounter))
countList = []

for currIp in uniqIps:
    countList.append([ipAddressCounter.count(currIp), "\t - \t" + currIp])

# inverse sort order
countList.sort(reverse=True)

for i in countList:
    print(str(i[0]) + i[1])

# remove all temporary files
for tmpFile in allTempFiles:
    os.remove(tmpFile)

if (args.execute):
    # remove empty directories
    for directory in os.scandir(args.output):
        if os.path.isdir(directory) and not os.listdir(directory):
            os.rmdir(directory)

