from piqueserver.networkdict import NetworkDict
import unittest


class TestNetworkDict(unittest.TestCase):

    def test_read_make_list(self):
        ban_list = [
            ["GOD", "177.47.27.223", ": esp hacker", 1511717871.435394],
            ["Tragon700", "187.16.185.94", ": AIMBOT", 1511718148.115572],
            ["Bradley", "94.193.254.118", ": ESP", 1511716740.165356],
            ["GOD", "189.24.61.113", ": ANT BAN", 1511718023.381783],
            ["RUszaj SIe", "188.146.106.109",
             ": Sle auto-headshot auto-kill", 1511718234.179913],
            ["Dj_Hazel_PL", "185.46.170.234", ": Hack", 1511715860.348984],
            ["(unknown)", "178.63.171.105", ": Hack", 1511716248.032651],
            ["Ken Kaneki", "177.222.250.65", ": kaneki afk", 1511718856.598152],
            ["panic-recover", "172.17.0.1", ": 10", 1512040137.320614],
        ]
        networkdict = NetworkDict()
        networkdict.read_list(ban_list)
        self.assertEqual(ban_list, networkdict.make_list())

    def test_get_set(self):
        networkdict = NetworkDict()
        values = ('GOD', ': esp hacker', 1511717871.435394)
        networkdict["177.47.27.223/24"] = values
        assert values == networkdict["177.47.27.223"]

    def test_get_nonexisting(self):
        networkdict = NetworkDict()
        self.assertRaises(KeyError, lambda: networkdict["127.0.0.1"])

    def test_del(self):
        networkdict = NetworkDict()
        networkdict["177.47.27.223"] = [
            'GOD', ': esp hacker', 1511717871.435394]
        del networkdict["177.47.27.223"]
        self.assertRaises(KeyError, lambda: networkdict["177.47.27.223"])

    def test_remove(self):
        networkdict = NetworkDict()
        networkdict["177.47.27.223"] = [
            'GOD', ': esp hacker', 1511717871.435394]
        removed = networkdict.remove("177.47.27.223")
        self.assertRaises(KeyError, lambda: networkdict["177.47.27.223"])
        self.assertEqual(len(networkdict), 0)
        self.assertEqual(str(removed[0][0]), "177.47.27.223/32")
        self.assertEqual(removed[0][1],
            ['GOD', ': esp hacker', 1511717871.435394])

    def test_pop(self):
        networkdict = NetworkDict()
        networkdict["177.47.27.223"] = [
            'GOD', ': esp hacker', 1511717871.435394]
        networkdict.pop()
        self.assertRaises(KeyError, lambda: networkdict["177.47.27.223"])

    def test_contains_nonexisting(self):
        networkdict = NetworkDict()
        self.assertEqual(("177.47.27.223" in networkdict), False)

    def test_contains_existing(self):
        networkdict = NetworkDict()
        networkdict["177.47.27.223"] = [
            'GOD', ': esp hacker', 1511717871.435394]
        self.assertEqual(("177.47.27.223" in networkdict), True)

    def test_contains_iprange(self):
        networkdict = NetworkDict()
        cases = [
            # Start IP: 56.0.0.0 End IP: 56.255.255.255
            {"iprange": "56.0.0.0/8", "within": "56.200.0.1", "outside": "57.200.0.1"},
            # Start IP: 127.0.0.0 End IP: 127.0.255.255
            {"iprange": "127.0.0.1/16", "within": "127.0.232.225",
                "outside": "127.1.232.225"},
            # Start IP: 127.0.0.0 End IP: 127.0.0.255
            {"iprange": "172.0.0.1/24", "within": "172.0.0.22",
                "outside": "127.1.232.225"}
        ]
        for case in cases:
            networkdict[case["iprange"]] = [
                'GOD', ': esp hacker', 1511717871.435394]
            self.assertEqual((case["within"] in networkdict), True)
            self.assertEqual((case["outside"] in networkdict), False)
