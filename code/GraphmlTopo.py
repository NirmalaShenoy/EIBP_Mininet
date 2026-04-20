#!/usr/bin/env python3
"""
One additional argument is required to run this script:
the path to a GraphML file.

Then, this script automatically configures the network emulated in Mininet
and runs the appropriate protocol(s).
"""

# the following are required imports
from mininet.topo import (
    Topo,
)  # this is the Topo class, which is inherited by GraphmlTopo
import xml.dom.minidom  # To parse the GraphML file
from sys import argv  # get the cmdline arguments - argv[1] is the GraphML file
from mininet.net import Mininet  # for Mininet to function
from time import sleep  # to delay as needed for the network to stabilize
from mininet.cli import CLI  # used for Mininet CLI to function
from subprocess import call  # just used to terminate Mininet at the end


# this is the inherited class from Topo to work with GraphML
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


# if the arguments are correct...
if len(argv) == 2:
    topo = GraphmlTopo()  # initialize the topology
    net = Mininet(topo=topo)  # initialize Mininet
    net.start()  # start Mininet

    # disable IP forwarding on all devices (routers and hosts)
    for host in net.hosts:
        host.cmd(["sysctl", "-w", "net.ipv4.ip_forward=0"])

    core_routers = [
        host for host in net.hosts if host.name[0] == "C"
    ]  # get the core routers
    dist_routers = [
        host for host in net.hosts if host.name[0] == "D"
    ]  # get the distribution routers
    access_routers = [
        host for host in net.hosts if host.name[0] == "A"
    ]  # get the access routers
    hosts = [host for host in net.hosts if host.name[0] == "H"]  # get the hosts

    # loop through the access routers and configure the gateway IP & CIDR
    # on the interface directly connected to each host
    for access_router in access_routers:
        gateway_with_cidr = "192.168." + str(int(access_router.name[1:])) + ".254/24"
        interface = access_router.name + "-eth0"
        access_router.cmd(["ip", "addr", "add", gateway_with_cidr, "dev", interface])

    # loop through and configure the IP & CIDR,
    # and then configure the default gateway of each host
    for host in hosts:
        prefix = "192.168." + str(int(host.name[1:])) + "."
        ip = prefix + "1"
        gateway = prefix + "254"
        ip_with_cidr = ip + "/24"
        interface = host.name + "-eth0"
        host.cmd(["ip", "addr", "add", ip_with_cidr, "dev", interface])
        host.cmd(["ip", "route", "add", "default", "via", gateway, "dev", interface])

        # this displays what was just done
        print(
            "Host: "
            + host.name
            + " with IP address: "
            + ip_with_cidr
            + " and the default gateway: "
            + gateway
        )
    # this is extra space for proper formatting
    print()

    # this loops through and configures the core routers
    # in EIBP, they each have a label
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
    sleep(
        20
    )  # delays like this are needed to ensure the network has had time to stabilize

    # this loops through the distribution routers
    # they have virtually no special configuration for any of them in EIBP
    for dist_router in dist_routers:
        with open("../logs/" + dist_router.name + ".txt", "w") as logfile:
            dist_router.popen(
                ["./MNLR", "-T", "2", "-N", "1"], stdout=logfile, stderr=logfile
            )
    # this announces that the distribution router assignment is complete
    print("Assignment for Distribution Routers done.")
    print()
    sleep(20)

    # this loops through the final category of routers, the access routers,
    # which require an IP & CIDR for the interface to function with IP,
    # as EIBP is IP-agnostic
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
    sleep(120)

    # begin the CLI
    CLI(net)

    # when the CLI is exited, terminate EIBP...
    call(["killall", "MNLR"])

    # then stop the network
    net.stop()

# if the command is entered incorrectly...
else:
    # display the usage
    print("Usage: " + argv[0] + " topology.graphml")
