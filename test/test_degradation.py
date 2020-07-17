

import unittest

from pof.degradation import Degradation

class TestDegradation(unittest.TestCase):

    def test_package_imports_correctly(self):
        self.assertTrue(True)

    def test_instantiate(self):
        d = Degradation()
        self.assertTrue(True)
        
    # Check whole degradation
    # test_starts_perfect_ends_perfect
    # test_starts_perfect_ends_partial
    # test_starts_perfect_ends_failed
    # test_starts_partial_ends_partial
    # test_starts_partial_ends_partial
    # test_starts_partial_ends_failed

    # test_perfect_prior_to_start
    # test_partial_prior_to_start


    # *********** Test the condition limits ******************
    def test_condition_starts_zero(self):
        d = Degradation(perfect=0, limit=100, cond_profile_type='linear', cond_profile_params =[10])
        self.assertEqual(d.current(), 0)

    def test_condition_starts_zero_does_not_breach_limit(self):
        d = Degradation(perfect=0, limit=100, cond_profile_type='linear', cond_profile_params =[10])
        d.sim(100)
        self.assertEqual(d.current(), 100)

    def test_condition_starts_positive(self):
        d = Degradation(perfect=100, limit=0, cond_profile_type='linear', cond_profile_params =[-10])
        self.assertEqual(d.current(), 100)

    def test_condition_starts_positive_does_not_breach_limit(self):
        d = Degradation(perfect=100, limit=0, cond_profile_type='linear', cond_profile_params =[-10])
        d.sim(100)
        self.assertEqual(d.current(), 0)

    # **************** Test the reset functions ***********************

    def test_reset(self):
        d = Degradation(perfect=100, limit=0, cond_profile_type='linear', cond_profile_params =[-10])
        d.sim(10)
        d.reset()
        self.assertEqual(d.current(),100)

    def test_reset_(self):
        d = Degradation(perfect=100, limit=0, cond_profile_type='linear', cond_profile_params =[-10])
        d.sim(10)
        d.reset()
        self.assertEqual(d.current(),100)

    # ************** Test the accumulation functions ******************

    def test_accumulate_time(self):
        self.assertEqual(False)

if __name__ == '__main__':
    unittest.main()