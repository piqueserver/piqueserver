from collections import OrderedDict

from ipaddress import ip_network, ip_address

def get_cidr(network):
    if network.prefixlen == 32:
        return str(network.network_address)
    return str(network)

# Note: Network objects cannot have any host bits set without strict=False.
# More info: https://docs.python.org/3/howto/ipaddress.html#defining-networks


class NetworkDict(object):
    def __init__(self):
        # Bans are split up over two dicts
        self.networks = []
        self.addresses = OrderedDict()
        # to make undo work properly,
        self.last_was_network = False

    def read_list(self, values):
        for item in values:
            self[item[1]] = [item[0]] + item[2:]

    def make_list(self):
        values = []
        for network, value in self.items():
            values.append([value[0]] + [network] + list(value[1:]))
        return values

    def remove(self, key):
        """remove a key from the networkdict and return the removed items"""
        ip = ip_network(str(key), strict=False)
        networks = []
        results = []
        for item in self.networks:
            network, _value = item
            if ip in network or ip == network:
                # this value should be removed
                results.append(item)
            else:
                # keep this value in the networkdict
                networks.append(item)
        self.networks = networks
        return results

    def __setitem__(self, key, value):
        network = ip_network(str(key), strict=False)

        if network.prefixlen == 32:
            self.addresses[ip_address(key)] = value
        else:
            self.networks.append((network, value))

    def __getitem__(self, key):
        return self.get_entry(key)

    def get_entry(self, key):
        ip = ip_address(str(key))

        try:
            return self.addresses[ip]
        except KeyError:
            for entry in self.networks:
                network, _value = entry
                if ip in network:
                    return entry

        raise KeyError(key)

    def __len__(self):
        return len(self.networks)

    def __delitem__(self, key):
        ip = ip_address(str(key))
        try:
            del self.addresses[ip]
        except KeyError:
            self.networks = [item for item in self.networks if ip not in item[0]]

    def pop(self):
        # TODO: undo networks too
        network, value = self.addresses.popitem(last=True)
        return str(network), value

    def items(self):
        for network, value in self.networks:
            yield get_cidr(network), value
        for address, value in self.addresses.items():
            yield str(address), value
    iteritems = items

    def __contains__(self, key):
        try:
            self.get_entry(key)
            return True
        except KeyError:
            return False
