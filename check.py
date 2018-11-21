import pandas as pd
import json
import numpy as np

# https://stackoverflow.com/a/43621819/209184
def deep_get(_dict, keys, default=None):
  for key in keys:
    if isinstance(_dict, dict):
      _dict = _dict.get(key, default)
    else:
      return default
  return _dict

def parse_date(date_string, default=None):
  try:
    return pd.Timestamp.strptime(date_string, '%Y-%m-%dT%H:%M:%S.000Z')
  except ValueError:
    return default

def reverse(_array):
  return _array[::-1]

def query(params):
  # Use the API key to perform a query on the Check API.
  # Apply the GraphQL query in check.gql.
  team = params['team']
  key = params['key']
  return json.load(open('./test_check.json'))

def flatten(raw):
  # Convert the GraphQL result to a Pandas DataFrame.
  df = []
  for project in raw['data']['team']['projects']['edges']:
    for media in project['node']['project_medias']['edges']:
      metadata = json.loads(media['node']['metadata'])
      df.append({
        'project': project['node']['title'],
        'title': metadata['title'],
        'date_added': pd.Timestamp.fromtimestamp(int(media['node']['created_at'])),
        'status': media['node']['last_status'],
        'content': media['node']['media']['quote'] if media['node']['report_type'] == 'claim' else metadata['description'],
        'url': {
          'uploadedimage': media['node']['media']['picture'],
          'link': media['node']['media']['url']
        }.get(media['node']['report_type']),
        'type': media['node']['media']['embed']['provider'] if media['node']['report_type'] == 'link' else media['node']['report_type'],
        'date_published': parse_date(deep_get(media, ['node', 'media', 'embed', 'published_at'], '')),
        'tags': ', '.join(map(lambda t: t['node']['tag_text'], reverse(media['node']['tags']['edges']))),
        'count_contributors': np.unique(map(lambda l: l['node']['user']['id'], media['node']['log']['edges'])).size,
        'count_notes': len(media['node']['comments']['edges']),
        'count_tasks': len(media['node']['tasks']['edges']),
        'count_tasks_completed': len([t for t in media['node']['tasks']['edges'] if t['node']['status'] == 'resolved'])
      })
  return pd.DataFrame(df)

def render(table, params):
  return flatten(query(params))
