from pyspades.ipaddr import IPNetwork

cache = {}

def get_network(cidr):
    try:
        return cache[cidr]
    except KeyError:
        network = IPNetwork(cidr)
        cache[cidr] = network
        return network

def get_cidr(network):
    if network._prefixlen == 32:
        return str(network.ip)
    return str(network)

class NetworkDict(object):
    def __init__(self):
        self.networks = []
    
    def read_list(self, values):
        for item in values:
            self[item[1]] = [item[0]] + item[2:]
        
    def make_list(self):
        values = []
        for network, value in self.iteritems():
            values.append([value[0]] + [network] + list(value[1:]))
        return values
    
    def remove(self, key):
        ip = get_network(key)
        networks = []
        results = []
        for item in self.networks:
            network, value = item
            if ip in network:
                results.append(item)
            else:
                networks.append(item)
        self.networks = networks
        return results
    
    def __setitem__(self, key, value):
        self.networks.append((get_network(key), value))
    
    def __getitem__(self, key):
        return self.get_entry(key)[1]
    
    def get_entry(self, key):
        ip = get_network(key)
        for entry in self.networks:
            network, value = entry
            if ip in network:
                return entry
        raise KeyError()
    
    def __len__(self):
        return len(self.networks)
    
    def __delitem__(self, key, value):
        ip = get_network(key)
        self.networks = [item for item in self.networks if ip not in item]
    
    def pop(self, *arg, **kw):
        network, value = self.networks.pop(*arg, **kw)
        return get_cidr(network), value
    
    def iteritems(self):
        for network, value in self.networks:
            yield get_cidr(network), value
    
    def __contains__(self, key):
        try:
            self.get_entry(key)
            return True
        except KeyError:
            return False
