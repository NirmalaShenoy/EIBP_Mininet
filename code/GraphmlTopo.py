#!/usr/bin/env python3
"""Custom topology built based on the content of a GraphML file

Two arguments are required, in the following order:
1. the path the graphML file.
2. The naming prefix of the hosts, if there are hosts. If there are no hosts, just simply add None.

Adding a topology with hosts in it (ex: host prefix is h, for h1, h2, etc.):
sudo mn --custom GraphmlTopo.py --topo=graphmltopo,"/home/pjw7904/MTP-Mininet/graphs/host_test.graphml",h
"""

from mininet.topo import Topo
import xml.dom.minidom  # To parse the GraphML file
from sys import argv
from mininet.net import Mininet
from time import sleep
from mininet.cli import CLI
from subprocess import call


class GraphmlTopo(Topo):
    "Build a Mininet network with a GraphML file"

    def build(self, clientPrefix=None):
        "Create a custom topo from a GraphML file"

        # Use an XML parser to parse the GraphML file
        graphmlFile = xml.dom.minidom.parse(argv[1])

        # Find all edges via the edge tag, add as Hosts and Links to Mininet network
        edges = graphmlFile.getElementsByTagName("edge")
        for edge in edges:

            # Add the nodes to the network
            sourceNode = self.defineNode(edge.getAttribute("source"), clientPrefix)
            targetNode = self.defineNode(edge.getAttribute("target"), clientPrefix)

            # Connect them together
            self.addLink(sourceNode, targetNode)

    def defineNode(self, nodeName, clientPrefix):
        "Determines if the node in question is a Host or Switch"

        # If the node is a client, add as a Mininet Host on the network
        if clientPrefix is not None and nodeName.startswith(clientPrefix):
            node = self.addHost(nodeName)
        # If the node is a switch, add as a Mininet Switch on the network
        else:
            node = self.addNode(nodeName)

        return node


if len(argv) == 2:
    topo = GraphmlTopo()
    net = Mininet(topo=topo)
    net.start()

    for host in net.hosts:
        host.cmd(["sysctl", "-w", "net.ipv4.ip_forward=0"])

    core_routers = [host for host in net.hosts if host.name[0] == "C"]
    dist_routers = [host for host in net.hosts if host.name[0] == "D"]
    access_routers = [host for host in net.hosts if host.name[0] == "A"]
    hosts = [host for host in net.hosts if host.name[0] == "H"]

    for access_router in access_routers:
        gateway_with_cidr = "192.168." + str(int(access_router.name[1:])) + ".254/24"
        interface = access_router.name + "-eth0"
        access_router.cmd(["ip", "addr", "add", gateway_with_cidr, "dev", interface])

    for host in hosts:
        prefix = "192.168." + str(int(host.name[1:])) + "."
        ip = prefix + "1"
        gateway = prefix + "254"
        ip_with_cidr = ip + "/24"
        interface = host.name + "-eth0"
        host.cmd(["ip", "addr", "add", ip_with_cidr, "dev", interface])
        host.cmd(["ip", "route", "add", "default", "via", gateway, "dev", interface])
        print(
            "Host: "
            + host.name
            + " with IP address: "
            + ip_with_cidr
            + " and the default gateway: "
            + gateway
        )
    print()

    for core_router in core_routers:
        with open("../logs/" + core_router.name + ".txt", "w") as logfile:
            core_router.popen(
                ["./MNLR", "-T", "1", "-L", "1." + core_router.name[1:], "-N", "1"],
                stdout=logfile,
                stderr=logfile,
            )
        print(
            "Core Router: "
            + core_router.name
            + " with label: 1."
            + core_router.name[1:]
        )
    print()
    sleep(20)

    for dist_router in dist_routers:
        with open("../logs/" + dist_router.name + ".txt", "w") as logfile:
            dist_router.popen(
                ["./MNLR", "-T", "2", "-N", "1"], stdout=logfile, stderr=logfile
            )
    print("Assignment for Distribution Routers done.")
    print()
    sleep(20)

    for access_router in access_routers:
        gateway = "192.168." + str(int(access_router.name[1:])) + ".254"
        gateway_with_cidr = gateway + "/24"
        interface = access_router.name + "-eth0"
        with open("../logs/" + access_router.name + ".txt", "w") as logfile:
            access_router.popen(
                ["./MNLR", "-T", "3", "-N", "0", gateway, "24", interface],
                stdout=logfile,
                stderr=logfile,
            )
        print(
            "Access Router: "
            + access_router.name
            + " with IP address: "
            + gateway_with_cidr
        )
    print()
    sleep(20)

    CLI(net)

    call(["killall", "MNLR"])

    net.stop()


else:
    print("Usage: " + argv[0] + " topology.graphml")
