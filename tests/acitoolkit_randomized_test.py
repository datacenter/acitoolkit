from acitoolkit_test import TestLiveAPIC
from acitoolkit import Tenant
import unittest


class TestRandomizationCleanup(TestLiveAPIC):
    """
    Tests used in conjunction with randomized configurations
    """
    def test_verify_all_tenants_deleted(self):
        """
        Test that all of the randomied tenants have been deleted
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        for tenant in tenants:
            self.assertFalse(tenant.name.startswith('acitoolkitrandomized-'))

if __name__ == '__main__':
    unittest.main()
