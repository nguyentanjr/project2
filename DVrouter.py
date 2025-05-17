####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

import json
from router import Router
from packet import Packet


class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        super().__init__(addr, heartbeat_time)
        # Distance vector: maps destination to (cost, next_hop)
        self.distance_vector = {addr: (0, None)}  # Distance to self is 0
        # Neighbors: maps port to (neighbor_addr, cost)
        self.neighbors = {}
        self.last_sent_time = 0
        self.heartbeat_time = heartbeat_time
        self.INFINITY = 16  # Standard infinity value for RIP

    def handle_new_link(self, port, endpoint, cost):
        # Add new neighbor
        self.neighbors[port] = (endpoint, cost)
        
        # Update distance vector
        if endpoint not in self.distance_vector or cost < self.distance_vector[endpoint][0]:
            self.distance_vector[endpoint] = (cost, endpoint)
            self.broadcast_dv()

    def handle_remove_link(self, port):
        if port in self.neighbors:
            neighbor = self.neighbors[port][0]
            del self.neighbors[port]
            
            # Remove routes through this neighbor
            changed = False
            for dst in list(self.distance_vector.keys()):
                if dst != self.addr and self.distance_vector[dst][1] == neighbor:
                    del self.distance_vector[dst]
                    changed = True
            
            if changed:
                self.broadcast_dv()

    

    def handle_time(self, time_ms):
        # Send periodic updates
        if time_ms - self.last_sent_time >= self.heartbeat_time:
            self.broadcast_dv()
            self.last_sent_time = time_ms

    def broadcast_dv(self):
        # Create and send distance vector to all neighbors
        dv_str = json.dumps({str(dst): cost for dst, (cost, _) in self.distance_vector.items()})
        for port in self.neighbors:
            packet = Packet(Packet.ROUTING, self.addr, self.neighbors[port][0], dv_str)
            self.send(port, packet)
    
    def __repr__(self):
        return f"DVrouter(addr={self.addr}, dv={self.distance_vector})"
