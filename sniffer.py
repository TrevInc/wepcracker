from subprocess import Popen, PIPE

from scapy.all import *
from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11ProbeResp, Dot11Elt

from interface import Interface


__author__ = 'michael'
aplist = []
aps = {}


def getap(pkt):
    global aplist
    # print pkt.summary()
    if 'Salerno' in pkt.summary():
        pass
    if pkt.haslayer(Dot11):
        if pkt.type == 0 and pkt.subtype == 8:
            if pkt.addr2 not in aplist:
                aplist.append(pkt.addr2)
                print "BSSID: %s SSID: %s" % (pkt.addr2, pkt.info)




def startmonmode(iface):
    os.system('ifconfig %s down' % iface)
    os.system('iwconfig %s mode monitor' % iface)
    os.system('ifconfig %s up' % iface)


def iwconfig():
    devnull = open(os.devnull, 'w')
    lst = []

    cmd = Popen(['iwconfig'], stdout=PIPE, stderr=devnull)
    for line in cmd.communicate()[0].split('\n\n'):
        tmpiface = Interface(None, None, None, None)
        line = line.strip()

        if len(line) == 0:
            continue

        ifname = re.search('^([A-Za-z0-9]+)', line)
        ifessid = re.search('ESSID:"([A-Za-z0-9]+)"', line)
        ifmode = re.search('Mode:([A-Za-z]+)', line)
        ifbssid = re.search('Access Point: ([0-9:A-F]+)', line)

        if ifname is not None:
            tmpiface.name = ifname.group(1)

            if ifessid is not None:
                tmpiface.essid = ifessid.group(1)

            if ifmode is not None:
                tmpiface.mode = ifmode.group(1)

            if ifbssid is not None:
                tmpiface.bssid = ifbssid.group(1)

            lst.append(tmpiface)

    devnull.close()
    return lst


def main():
    interfaces = iwconfig()

    for i in interfaces:
        print i.tostring()

    pick = input('Pick one (starting from 0): ')
    pick = interfaces[pick].name

    print 'putting %s in mon mode' % pick
    startmonmode(pick)
    conf.iface = pick
    print 'ok I should be printing out packets now'
    sniff()


if __name__ == '__main__':
    main()
