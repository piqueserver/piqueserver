from ipaddress import ip_network, ip_address
from collections import OrderedDict

def get_cidr(network):
    if network.prefixlen == 32:
        return str(network.network_address)
    return str(network)

# Note: Network objects cannot have any host bits set without strict=False.
# More info: https://docs.python.org/3/howto/ipaddress.html#defining-networks


class NetworkDict:
    def __init__(self):
        self.networks = OrderedDict()

    def read_list(self, values):
        for index, item in enumerate(values):
            if len(item) < 4:
                raise ValueError("Invalid ban entry. index: {} item: {}\nEntry format needs to be [name, ip, reason, time]".format(index, item))
            self[item[1]] = [item[0]] + item[2:]

    def make_list(self):
        values = []
        for network, value in self.iteritems():
            values.append([value[0]] + [network] + list(value[1:]))
        return values

    def remove(self, key):
        """remove a key from the networkdict and return the removed items"""
        ip = ip_network(str(key), strict=False)
        results = []
        # There are 32 possible networks for each IP address in CIDR. This is
        # small enough that we can just loop through all of them to get an
        # unelegant constant time lookup for IP addresses.
        #
        # This loop could be sped up by a lot by using a (ip, mask) int tuple
        # instead of constantly creating new IPNetwork objects with .supernet()
        #
        # When in doubt, use brute force - Ken Thompson
        for _ in range(0, 32):
            try:
                elem = self.networks.pop(ip)
            except KeyError:
                pass
            else:
                results.append([ip, elem])
            ip = ip.supernet()
        return results

    def __setitem__(self, key, value):
        self.networks[ip_network(str(key), strict=False)] = value

    def __getitem__(self, key):
        return self.get_entry(key)[1]

    def get_entry(self, key):
        ip = ip_network(str(key))
        # See comment for remove()
        for _ in range(0, 32):
            try:
                return self.networks[ip]
            except KeyError:
                pass
            ip = ip.supernet()
        raise KeyError(key)

    def __len__(self):
        return len(self.networks)

    def __delitem__(self, key):
        ip = ip_network(str(key), strict=False)
        self.networks.popitem(ip)

    def pop(self, *arg, **kw):
        network, value = self.networks.popitem(*arg, **kw)
        return get_cidr(network), value

    def iteritems(self):
        for network, value in self.networks.items():
            yield get_cidr(network), value

    def __contains__(self, key):
        try:
            self.get_entry(key)
            return True
        except KeyError:
            return False
