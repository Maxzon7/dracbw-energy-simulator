# run_tests.py
import unittest
import sys

def main():
    print("======================================================================")
    print("Running Energy Simulator Automated Verification Suite")
    print("======================================================================\n")
    
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n======================================================================")
    if result.wasSuccessful():
        print("Verification Successful! All unit tests passed.")
        print("======================================================================")
        sys.exit(0)
    else:
        print("Verification Failed. Some tests did not pass.")
        print("======================================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
