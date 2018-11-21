import unittest
import numpy as np
import pandas as pd
import json
from pandas.testing import assert_frame_equal
from check import render, query, flatten

class TestCheck(unittest.TestCase):
  def setUp(self):
    self.data = json.load(open('./test_check.json'))

  def test_flatten(self):
    print(flatten(self.data)[['count_contributors', 'count_notes', 'count_tasks', 'count_tasks_completed']])

if __name__ == '__main__':
    unittest.main()
