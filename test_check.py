import unittest
import numpy as np
import pandas as pd
import json
from pandas.testing import assert_frame_equal
from check import render, query, flatten

class TestCheck(unittest.TestCase):
  def setUp(self):
    self.file = open('./test_check.json')
    self.data = json.load(self.file)

  def tearDown(self):
    self.file.close()

  def test_flatten(self):
    print(flatten(self.data)[['comments']])

if __name__ == '__main__':
    unittest.main()
