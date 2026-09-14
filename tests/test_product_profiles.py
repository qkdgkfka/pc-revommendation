import unittest

import server_fixed as server


class RetailPerformanceProfileTests(unittest.TestCase):
    def test_unknown_gpu_does_not_borrow_neighbor_model_benchmark(self):
        self.assertIsNone(server.performance_reference_for_danawa_product("gpu", "GeForce RTX 5050 8GB"))

    def test_gpu_memory_variants_use_separate_profiles(self):
        small = server.performance_reference_for_danawa_product("gpu", "MSI GeForce RTX 5060 Ti 8GB")
        large = server.performance_reference_for_danawa_product("gpu", "MSI GeForce RTX 5060 Ti 16GB")
        self.assertEqual("gpu_rtx5060ti8", small["id"])
        self.assertEqual("gpu_rtx5060ti16", large["id"])
        self.assertIsNone(server.performance_reference_for_danawa_product("gpu", "RTX 5060 Ti"))

    def test_cpu_suffix_is_preserved(self):
        known = server.performance_reference_for_danawa_product("cpu", "AMD 라이젠7 9800X3D (정품)")
        self.assertEqual("cpu_r7_9800x3d", known["id"])
        self.assertIsNone(server.performance_reference_for_danawa_product("cpu", "AMD Ryzen 7 9800X"))

    def test_unknown_capacity_does_not_inherit_ram_reference_specs(self):
        self.assertIsNone(server.performance_reference_for_danawa_product("ram", "Samsung DDR5-5600"))


if __name__ == "__main__":
    unittest.main()
