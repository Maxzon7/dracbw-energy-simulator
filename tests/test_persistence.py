# tests/test_persistence.py
import unittest
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPersistence(unittest.TestCase):
    def test_legacy_battery_config_fallback(self):
        # Replicates the parsing fallback logic from tab2_scenarios.py
        # Scenario A: Legacy battery config has only 'b_cap', missing 'num_batteries' and 'cap_per_module'
        legacy_b = {
            "b_cap": 300.0,
            "b_pwr": 100.0,
            "shaving_threshold": 80.0
        }
        
        # Test logic mimicking tab2_scenarios.py parsing
        num_bats = int(legacy_b.get("num_batteries", 10))
        cap_per_module = float(legacy_b.get("cap_per_module", float(legacy_b.get("b_cap", 200.0)) / num_bats))
        
        self.assertEqual(num_bats, 10)
        self.assertEqual(cap_per_module, 30.0) # 300.0 / 10 = 30.0
        
    def test_modern_battery_config_mapping(self):
        # Scenario B: Modern battery config has explicit modules configs
        modern_b = {
            "num_batteries": 5,
            "cap_per_module": 40.0,
            "b_cap": 200.0
        }
        
        num_bats = int(modern_b.get("num_batteries", 10))
        cap_per_module = float(modern_b.get("cap_per_module", float(modern_b.get("b_cap", 200.0)) / num_bats))
        
        self.assertEqual(num_bats, 5)
        self.assertEqual(cap_per_module, 40.0)

if __name__ == "__main__":
    unittest.main()
