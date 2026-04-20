#!/usr/bin/env python3
"""
One additional argument is required to run this script:
the path to a GraphML file.

Then, this script automatically configures the network emulated in Mininet
and runs the appropriate protocol(s).
"""

# the following are required imports
from mininet.node import (
    Node,
)  # this is the class for a Node, which will be inherited by FRRouter
from mininet.topo import (
    Topo,
)  # this is the Topo class, which is inherited by GraphmlTopo
import xml.dom.minidom  # To parse the GraphML file
from sys import argv  # get the cmdline arguments - argv[1] is the GraphML file
from mininet.net import Mininet  # for Mininet to function
from time import sleep  # to delay as needed for the network to stabilize
from mininet.cli import CLI  # used for Mininet CLI to function

router_i = 1  # this variable iterates through as an OSPF router ID


# some of this functions to inherit the existing class
class FRRouter(Node):
    def config(self, **params):
        # the initialize constructor of the inherited class is called
        super(FRRouter, self).config(**params)
        self.cmd(
            ["sysctl", "-w", "net.ipv4.ip_forward=1"]
        )  # enable IP forwarding on the routers
        filepath = "/etc/frr/" + self.name  # this is the filepath to the router
        self.cmd(
            ["mkdir", filepath]
        )  # this creates the directory corresponding to the filepath
        self.cmd(
            ["cp", "/etc/frr/daemons", "/etc/frr/vtysh.conf", filepath]
        )  # this copies the standard files needed to the filepath

        logpath = "/var/log/frr/" + self.name + ".log"
        ospfd_f_path = filepath + "/ospfd.conf"
        with open(ospfd_f_path, "w") as ospfd_f:
            ospfd_contents = "log file " + logpath + "\n"
            ospfd_f.write(ospfd_contents)

        quotedname = '"' + self.name + '"'  # this is a quoted name for the namespace
        self.cmd(
            ["/usr/lib/frr/frrinit.sh", "start", quotedname]
        )  # this starts FRR on the namespace

        global router_i  # this refers to the router_i variable declared earlier out of scope

        # the following configures OSPF & enables debugging
        self.cmd(
            [
                "vtysh",
                "-N",
                self.name,
                "-c",
                '"debug ospf packet all"',
                "-c",
                '"configure terminal"',
                "-c",
                '"router ospf"',
                "-c",
                ('"router-id ' + "1.1.1." + str(router_i) + '"'),
                "-c",
                '"exit"',
            ]
        )
        # increment the router_i variable by 1 each round
        router_i += 1

    def terminate(self):
        # quotedname is made again
        quotedname = '"' + self.name + '"'
        # then FRR is stopped on each namespace
        self.cmd(["/usr/lib/frr/frrinit.sh", "stop", quotedname])

        # the directory for the namespace is deleted
        filepath = "/etc/frr/" + self.name  # this is the filepath for the router
        self.cmd(["rm", "-rf", filepath])  # this removes the namespace directory

        # the terminate constructor of the inherited class is called
        super(FRRouter, self).terminate()


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
            # if the node is a router (not a host)...
            if nodeName[0] != "H":
                # create the node as a router
                node = self.addNode(nodeName, cls=FRRouter)
            else:
                # otherwise, create a host
                node = self.addNode(nodeName)

        return node


# if the arguments are correct...
if len(argv) == 2:
    topo = GraphmlTopo()  # initialize the topology
    net = Mininet(topo=topo)  # initialize Mininet
    net.start()  # start Mininet

    # remove the incorrect IP addresses on each interface,
    # and disable IP forwarding on the hosts (just in case)
    for host in net.hosts:
        for intf in host.intfList():
            host.cmd(["ip", "addr", "flush", "dev", intf.name])
        if host.name[0] == "H":
            host.cmd(["sysctl", "-w", "net.ipv4.ip_forward=0"])

    # this is the iterator variable
    i = 0

    # loop through the links and configure the routers and hosts
    for link in net.links:
        # get the interfaces from the link
        interfaces = str(link.intf1.link).split("<->")

        gateway1_with_cidr = (
            "192.168." + str(i + 1) + ".254/24"
        )  # get the gateway IP address with CIDR

        # set the IP & CIDR of the gateway to the interface
        link.intf1.node.cmd(
            ["ip", "addr", "add", gateway1_with_cidr, "dev", interfaces[0]]
        )

        # enable OSPF on the interface
        link.intf1.node.cmd(
            [
                "vtysh",
                "-N",
                link.intf1.node.name,
                "-c",
                '"configure terminal"',
                "-c",
                '"interface ' + interfaces[0] + '"',
                "-c",
                '"ip ospf area 0"',
                "-c",
                '"exit"',
            ]
        )

        # if the second interface is a router (not a host)...
        if interfaces[1][0] != "H":
            gateway2_with_cidr = (
                "192.168." + str(i + 1) + ".253/24"
            )  # get the gateway IP address with CIDR

            # set the IP & CIDR of the gateway to the interface
            link.intf2.node.cmd(
                ["ip", "addr", "add", gateway2_with_cidr, "dev", interfaces[1]]
            )

            # enable OSPF on the interface
            link.intf2.node.cmd(
                [
                    "vtysh",
                    "-N",
                    link.intf2.node.name,
                    "-c",
                    '"configure terminal"',
                    "-c",
                    '"interface ' + interfaces[1] + '"',
                    "-c",
                    '"ip ospf area 0"',
                    "-c",
                    '"exit"',
                ]
            )
        # otherwise, if this is a host...
        else:
            # get the prefix (for the respective host and its default gateway)
            prefix = "192.168." + str(i + 1) + "."

            # the default gateway for the host
            gateway = prefix + "254"

            # the IP with CIDR of the host
            ip_with_cidr = prefix + "1/24"

            # configure the IP & CIDR on the interface
            link.intf2.node.cmd(
                ["ip", "addr", "add", ip_with_cidr, "dev", interfaces[1]]
            )

            # set the default gateway of the host
            link.intf2.node.cmd(
                ["ip", "route", "add", "default", "via", gateway, "dev", interfaces[1]]
            )
        # increment the iterator variable
        i += 1

    # delay two minutes to allow for the network to stabilize
    sleep(120)

    # begin the CLI
    CLI(net)

    # when the CLI is exited, stop the network
    net.stop()

# if the command is entered incorrectly...
else:
    # display the usage
    print("Usage: " + argv[0] + " topology.graphml")
