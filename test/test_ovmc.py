#!/usr/bin/env python

from boutiques import bosh
from unittest import TestCase
import os


class TestOvmc(TestCase):

    def test_ovmc(self):
        self.assertFalse(bosh(["test", "ovmc.json"]))
