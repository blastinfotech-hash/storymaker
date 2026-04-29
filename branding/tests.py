from django.test import TestCase

from .models import BrandGuide


class BrandGuideTests(TestCase):
    def test_get_active_creates_default_guide(self):
        guide = BrandGuide.get_active()

        self.assertTrue(guide.is_active)
        self.assertEqual(BrandGuide.objects.count(), 1)
