from pyspades.types import IDPool, AttributeSet, MultikeyDict
import unittest


class TestIDPool(unittest.TestCase):
    def test_start(self):
        pool = IDPool(start=5)
        self.assertEqual(5, pool.pop())

    def test_putting_back(self):
        pool = IDPool(start=5)
        self.assertEqual(5, pool.pop())
        self.assertEqual(6, pool.pop())
        pool.put_back(5)
        self.assertEqual(5, pool.pop())


class TestAttributeSet(unittest.TestCase):
    def test_set(self):
        atset = AttributeSet(["test", "set", "name"])
        self.assertTrue(atset.test)
        self.assertTrue(atset.set)
        self.assertTrue(atset.name)
        self.assertFalse(atset.wrong)

        self.assertFalse(atset.new)
        atset.new = False
        self.assertFalse(atset.new)
        atset.new = True
        self.assertTrue(atset.new)
        atset.new = 0
        self.assertFalse(atset.new)


class TestMultikeyDict(unittest.TestCase):
    def test_create(self):
        dic = MultikeyDict()
        dic[1, 'bar'] = 2
        self.assertEqual(dic[1], 2)
        self.assertIs(dic[1], dic['bar'])

    @unittest.expectedFailure
    def test_identity(self):
        dic = MultikeyDict()
        lst = ["hi"]
        dic["key", ("tup", "le")] = lst
        self.assertIs(dic["key"], lst)
        self.assertIs(dic["tup", "le"], lst)

    def test_assign_multiple(self):
        dic = MultikeyDict()
        dic[1, 'bar'] = 2
        with self.assertRaises(KeyError):
            dic[3, 'bar'] = 5

    def test_misc_funcs(self):
        dic = MultikeyDict()
        dic[1, 'bar'] = 2
        dic[3, 'baz'] = 5

        self.assertEqual(len(dic), 2)
        del dic[1]
        self.assertEqual(len(dic), 1)

        dic.clear()
        self.assertEqual(len(dic), 0)

    def test_get(self):
        dic = MultikeyDict()
        dic[7, 'egg'] = 42
        self.assertEqual(dic.get(7), 42)
        self.assertEqual(dic.get("egg"), 42)
        self.assertEqual(dic.get("spam", "def"), "def")
