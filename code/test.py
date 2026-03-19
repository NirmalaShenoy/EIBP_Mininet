#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call
import time

def myNetwork():

    net = Mininet( topo=None,
                   build=False)

    info( '*** Adding controller\n' )
    info( '*** Add switches\n')
    C1 = net.addHost('C1', cls=Node, ip=None)
    C1.cmd('sysctl -w net.ipv4.ip_forward=0')
    D1 = net.addHost('D1', cls=Node, ip=None)
    D1.cmd('sysctl -w net.ipv4.ip_forward=0')
    D2 = net.addHost('D2', cls=Node, ip=None)
    D2.cmd('sysctl -w net.ipv4.ip_forward=0')
    A1 = net.addHost('A1', cls=Node, ip=None)
    A1.cmd('sysctl -w net.ipv4.ip_forward=0')
    A2 = net.addHost('A2', cls=Node, ip=None)
    A2.cmd('sysctl -w net.ipv4.ip_forward=0')

    info( '*** Add hosts\n')
    h1 = net.addHost('h1', cls=Host, ip='192.168.0.1/24', defaultRoute='via 192.168.0.254')
    h2 = net.addHost('h2', cls=Host, ip='192.168.1.1/24', defaultRoute='via 192.168.1.254')

    info( '*** Add links\n')
    net.addLink(C1, D1)
    net.addLink(C1, D2)
    net.addLink(D1, A1)
    net.addLink(D2, A2)
    net.addLink(D1, A2)
    net.addLink(D2, A1)
    net.addLink(A1, h1)
    net.addLink(A2, h2)

    A1.setIP('192.168.0.254/24', intf='A1-eth2')
    A2.setIP('192.168.1.254/24', intf='A2-eth2')

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches\n')

    info( '*** Post configure switches and hosts\n')



    """
    popen must be used instead of cmd for this to work.
    a minimum delay of 5 seconds is necessary for
    the higher-tiered routers to send out join request,
    so the lower-tiered routers have had time to stabilize.
    """
    C1_file = open('C1.txt', 'w')
    C1_popen = C1.popen(['./EIBP', '-T', '1', '-L', '1.1', '-N', '1'], stdout=C1_file, stderr=C1_file)
    time.sleep(10)


    Drouter_cmd = ['./EIBP', '-T', '2', '-N', '1']

    D1_file = open('D1.txt', 'w')
    D1_popen = D1.popen(Drouter_cmd, stdout=D1_file, stderr=D1_file)
    time.sleep(10)

    D2_file = open('D2.txt', 'w')
    D2_popen = D2.popen(Drouter_cmd, stdout=D2_file, stderr=D2_file)
    time.sleep(10)



    A1_file = open('A1.txt', 'w')
    A1_popen = A1.popen(['./EIBP', '-T', '3', '-N', '0', '192.168.0.254', '24', 'A1-eth2'], stdout=A1_file, stderr=A1_file)
    time.sleep(10)

    A2_file = open('A2.txt', 'w')
    A2_popen = A2.popen(['./EIBP', '-T', '3', '-N', '0', '192.168.1.254', '24', 'A2-eth2'], stdout=A2_file, stderr=A2_file)
    time.sleep(10)


    CLI(net)


    C1_popen.terminate()
    D1_popen.terminate()
    D2_popen.terminate()
    A1_popen.terminate()
    A2_popen.terminate()

    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()

