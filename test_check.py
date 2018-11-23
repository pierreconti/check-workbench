import unittest
import numpy as np
import pandas as pd
import json
from pandas.testing import assert_frame_equal
from check import render, flatten

class FetchResult:
  def __init__(self, dataframe):
    self.dataframe = dataframe
    self.status = None

class TestCheck(unittest.TestCase):
  def setUp(self):
    self.file = open('./test_check.json')
    self.data = json.load(self.file)

  def tearDown(self):
    self.file.close()

  def test_flatten(self):
    df = flatten(self.data)

  def test_render(self):
    df = flatten(self.data)
    render(df, { 'anonymize': False }, fetch_result=FetchResult(df))
    render(df, { 'anonymize': True }, fetch_result=FetchResult(df))

if __name__ == '__main__':
    unittest.main()
