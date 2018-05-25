#!/usr/bin/env python

from boutiques import bosh
from unittest import TestCase
import os


class TestMcFlirt(TestCase):

    def run_command_test(self, command):
        process = subprocess.Popen(command, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        self.assertFalse(process.returncode)
        return process.stdout.read().decode("utf-8")


    def test_mcflirt(self):
        self.assertFalse(bosh(["test", "boutiques/mcflirt_ovmc.json"]))
	
