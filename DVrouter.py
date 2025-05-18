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
        Router.__init__(self, addr)
        # Véc tơ khoảng cách: ánh xạ đích đến (chi phí, next_hop)
        self.distance_vector = {addr: (0, None)}  # Distance to self is 0
        # Hàng xóm: ánh xạ cổng tới (neighbor_addr, cost)
        self.neighbors = {}
        self.last_sent_time = 0
        self.heartbeat_time = heartbeat_time
        self.INFINITY = 16  # Giá trị vô cực chuẩn cho RIP

    def handle_new_link(self, port, endpoint, cost):
        # Thêm hxom mới
        self.neighbors[port] = (endpoint, cost)
        
        # Cập nhật distance vector
        if endpoint not in self.distance_vector or cost < self.distance_vector[endpoint][0]:
            self.distance_vector[endpoint] = (cost, endpoint)
            self.broadcast_dv()

    def handle_remove_link(self, port):
        if port in self.neighbors:
            neighbor = self.neighbors[port][0]
            del self.neighbors[port]
            
            # Xóa các routes qua hàng xóm này
            changed = False
            for dst in list(self.distance_vector.keys()):
                if dst != self.addr and self.distance_vector[dst][1] == neighbor:
                    del self.distance_vector[dst]
                    changed = True
            
            if changed:
                self.broadcast_dv()

    def handle_packet(self, port, packet):
        if packet.is_traceroute:
            # Chuyển tiếp các gói traceroute dựa trên distance vector
            dst = packet.dst_addr
            if dst in self.distance_vector:
                cost, next_hop = self.distance_vector[dst]
                if next_hop is not None:  # We know a route
                    for p, (neighbor, _) in self.neighbors.items():
                        if neighbor == next_hop:
                            self.send(p, packet)
                            break
        elif packet.is_routing:
            # xử lý cập nhật định tuyến từ hàng xóm
            try:
                neighbor_dv = json.loads(packet.content)
                neighbor_addr = packet.src_addr
                
                # Cập nhật distance vector
                changed = False
                for dst, cost in neighbor_dv.items():
                    if dst != str(self.addr):  # Không cập nhật khoảng cách tới bản thân
                        neighbor_cost = self.neighbors[port][1]
                        new_cost = cost + neighbor_cost
                        
                        if dst not in self.distance_vector or new_cost < self.distance_vector[dst][0]:
                            self.distance_vector[dst] = (new_cost, neighbor_addr)
                            changed = True
                        elif self.distance_vector[dst][1] == neighbor_addr and new_cost != self.distance_vector[dst][0]:
                            # Cập nhật chi phí nếu next hop giống nhau
                            self.distance_vector[dst] = (new_cost, neighbor_addr)
                            changed = True
                
                # Nếu distance vector thay đổi , cập nhất broadcast
                if changed:
                    self.broadcast_dv()
            except json.JSONDecodeError:
                pass  

    def handle_time(self, time_ms):  # được gọi liên tục để xác định đủ thời gian gửi DV mới hay ko
        # Gửi các bản cập nhật định kỳ
        if time_ms - self.last_sent_time >= self.heartbeat_time:
            self.broadcast_dv()
            self.last_sent_time = time_ms

    def broadcast_dv(self):
        # Tạo và gửi distance vector đến tất cả các hàng xóm
        dv_str = json.dumps({str(dst): cost for dst, (cost, _) in self.distance_vector.items()})
        for port in self.neighbors:
            packet = Packet(Packet.ROUTING, self.addr, self.neighbors[port][0], dv_str)
            self.send(port, packet)
    
    def __repr__(self):
        return f"DVrouter(addr={self.addr}, dv={self.distance_vector})"