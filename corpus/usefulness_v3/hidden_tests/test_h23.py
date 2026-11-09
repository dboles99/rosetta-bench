import unittest

from solution import topo_order, layers, CycleError


class TestTopoOrder(unittest.TestCase):
    def test_chain(self):
        self.assertEqual(topo_order(["c", "b", "a"], [("a", "b"), ("b", "c")]), ["a", "b", "c"])

    def test_lexicographically_smallest_available_first(self):
        self.assertEqual(topo_order(["a", "b", "c"], [("b", "a")]), ["b", "a", "c"])
        self.assertEqual(topo_order(list("abcde"), [("e", "a"), ("d", "b")]), ["c", "d", "b", "e", "a"])

    def test_plain_string_order(self):
        self.assertEqual(topo_order(["9", "10"], []), ["10", "9"])

    def test_duplicates(self):
        self.assertEqual(topo_order(["a", "a", "b"], [("a", "b"), ("a", "b")]), ["a", "b"])

    def test_iterable_nodes(self):
        self.assertEqual(topo_order(iter(["b", "a"]), []), ["a", "b"])

    def test_empty(self):
        self.assertEqual(topo_order([], []), [])

    def test_unknown_node(self):
        with self.assertRaises(ValueError) as ctx:
            topo_order(["a"], [("a", "z")])
        self.assertTrue(str(ctx.exception).startswith("unknown node"), str(ctx.exception))
        self.assertNotIsInstance(ctx.exception, CycleError)

    def test_cycle_reports_blocked_nodes(self):
        with self.assertRaises(CycleError) as ctx:
            topo_order(["d", "c", "b", "a"], [("a", "b"), ("b", "c"), ("c", "b"), ("c", "d")])
        self.assertEqual(ctx.exception.nodes, ["b", "c", "d"])
        self.assertIsInstance(ctx.exception, ValueError)

    def test_self_loop(self):
        with self.assertRaises(CycleError) as ctx:
            topo_order(["x", "y"], [("x", "x")])
        self.assertEqual(ctx.exception.nodes, ["x"])

    def test_inputs_not_modified(self):
        nodes, edges = ["b", "a"], [("a", "b")]
        topo_order(nodes, edges)
        layers(nodes, edges)
        self.assertEqual((nodes, edges), (["b", "a"], [("a", "b")]))


class TestLayers(unittest.TestCase):
    def test_layers(self):
        edges = [("a", "c"), ("b", "c"), ("c", "d"), ("a", "d")]
        self.assertEqual(layers(["d", "c", "b", "a"], edges), [["a", "b"], ["c"], ["d"]])

    def test_longest_path_decides_layer(self):
        self.assertEqual(layers(["a", "b", "c"], [("a", "b"), ("b", "c"), ("a", "c")]), [["a"], ["b"], ["c"]])

    def test_independent_nodes_share_layer_sorted(self):
        self.assertEqual(layers(["z", "10", "9"], [("9", "z")]), [["10", "9"], ["z"]])

    def test_cycle(self):
        with self.assertRaises(CycleError) as ctx:
            layers(["a", "b", "c"], [("a", "b"), ("b", "a")])
        self.assertEqual(ctx.exception.nodes, ["a", "b"])

    def test_empty(self):
        self.assertEqual(layers([], []), [])


if __name__ == "__main__":
    unittest.main()
