####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################

import json
import networkx as nx
from router import Router
from packet import Packet


class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        super().__init__(addr, heartbeat_time)
        # Link state database: maps router_addr to its link state
        self.link_state_db = {}
        # Sequence numbers for each router's LSP
        self.sequence_numbers = {}
        # Neighbors: maps port to (neighbor_addr, cost)
        self.neighbors = {}
        self.last_sent_time = 0
        self.heartbeat_time = heartbeat_time
        # Initialize our own link state
        self.link_state_db[addr] = {}
        self.sequence_numbers[addr] = 0

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            # Forward traceroute packets based on our computed routes
            dst = packet.dst_addr
            next_hop = self.get_next_hop(dst)
            if next_hop is not None:
                for p, (neighbor, _) in self.neighbors.items():
                    if neighbor == next_hop:
                        self.send(p, packet)
                        break
        elif packet.is_routing:
            # Process link state packets
            try:
                lsp = json.loads(packet.content)
                src = lsp['src']
                seq = lsp['seq']
                links = lsp['links']
                
                # Check if this is a new LSP
                if src not in self.sequence_numbers or seq > self.sequence_numbers[src]:
                    # Update link state database
                    self.link_state_db[src] = links
                    self.sequence_numbers[src] = seq
                    
                    # Forward LSP to all neighbors except the one we received it from
                    for p, (neighbor, _) in self.neighbors.items():
                        if p != port:  # Don't send back to the source
                            self.send(p, packet)
            except (json.JSONDecodeError, KeyError):
                pass  # Invalid packet content

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        # Add new neighbor
        self.neighbors[port] = (endpoint, cost)
        
        # Update our link state
        self.link_state_db[self.addr][endpoint] = cost
        self.sequence_numbers[self.addr] += 1
        
        # Broadcast our updated link state
        self.broadcast_lsp()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port in self.neighbors:
            neighbor = self.neighbors[port][0]
            del self.neighbors[port]
            
            # Update our link state
            if neighbor in self.link_state_db[self.addr]:
                del self.link_state_db[self.addr][neighbor]
                self.sequence_numbers[self.addr] += 1
                self.broadcast_lsp()

    def handle_time(self, time_ms):
        """Handle current time."""
        # Send periodic updates
        if time_ms - self.last_sent_time >= self.heartbeat_time:
            self.broadcast_lsp()
            self.last_sent_time = time_ms

    def broadcast_lsp(self):
        # Create and send our link state packet
        lsp = {
            'src': self.addr,
            'seq': self.sequence_numbers[self.addr],
            'links': self.link_state_db[self.addr]
        }
        content = json.dumps(lsp)
        
        # Send to all neighbors
        for port in self.neighbors:
            packet = Packet(Packet.ROUTING, self.addr, self.neighbors[port][0], content)
            self.send(port, packet)

    def get_next_hop(self, dst):
        # Create graph from link state database
        G = nx.Graph()
        # Add all nodes first
        for router in self.link_state_db:
            G.add_node(router)
        # Add all edges
        for router, links in self.link_state_db.items():
            for neighbor, cost in links.items():
                if neighbor not in G:
                    G.add_node(neighbor)
                G.add_edge(router, neighbor, weight=cost)
        
        try:
            # Find shortest path
            path = nx.shortest_path(G, self.addr, dst, weight='weight')
            if len(path) > 1:
                return path[1]  # Return next hop
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        return None

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"LSrouter(addr={self.addr}, neighbors={self.neighbors})"
