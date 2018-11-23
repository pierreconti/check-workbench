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

def media_time_to_status(media, first=True):
  times = list(map(lambda l: l['node']['created_at'], [l for l in reverse(media['node']['log']['edges']) if l['node']['event_type'] == 'update_dynamicannotationfield']))
  if len(times) == 0:
    return None
  time = times[0] if first else times[-1]
  return pd.Timedelta(seconds=(int(time) - int(media['node']['created_at'])))

def format_comments(comments):
  if len(comments) == 0:
    return None
  if len(comments) > 1:
    comments[0] = '- ' + comments[0]
  return '\n- '.join(comments)

def task_comments(task):
  return format_comments(
    list(map(
      lambda l: json.loads(l['node']['annotation']['content'])['text'],
      [l for l in task['log']['edges'] if l['node']['event_type'] == 'create_comment']
    ))
  )

def media_comments(media):
  return format_comments(
    list(map(
      lambda c: json.loads(c['node']['content'])['text'],
      media['node']['comments']['edges']
    ))
  )

def task_answer(task):
  content = json.loads(task['first_response']['content'])
  for field in content:
    if field['field_name'].startswith('response_'):
      return field['formatted_value']
  return None

def media_tags(media):
  tags = reverse(media['node']['tags']['edges'])
  if len(tags) == 0:
    return None
  return ', '.join(map(lambda t: t['node']['tag_text'], tags))

def media_tasks(media):
  # Return a dict of all tasks in a single row
  tasks = {}
  for i, task in enumerate(reverse(media['node']['tasks']['edges'])):
    tasks['task_%(i)d_question' % { 'i': i+1 }] = task['node']['label']
    tasks['task_%(i)d_comments' % { 'i': i+1 }] = task_comments(task['node'])
    if task['node']['first_response']:
      tasks['task_%(i)d_answer' % { 'i': i+1 }] = task_answer(task['node'])
      tasks['task_%(i)d_date_answered' % { 'i': i+1 }] = pd.Timestamp.fromtimestamp(int(media['node']['created_at']))
  return tasks

def flatten(team):
  # Convert the GraphQL result to a Pandas DataFrame.
  df = []
  for project in team['data']['team']['projects']['edges']:
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
        'tags': media_tags(media),
        'comments': media_comments(media),
        'count_contributors': np.unique(map(lambda l: l['node']['user']['id'], media['node']['log']['edges'])).size,
        'count_notes': len(media['node']['comments']['edges']),
        'count_tasks': len(media['node']['tasks']['edges']),
        'count_tasks_completed': len([t for t in media['node']['tasks']['edges'] if t['node']['status'] == 'resolved']),
        'time_to_first_status': media_time_to_status(media, True),
        'time_to_last_status': media_time_to_status(media, False),
        **media_tasks(media),
      })
  return pd.DataFrame(df)

async def fetch(params, **kwargs):
  return flatten(query(params))

def render(table, params, *, fetch_result, **kwargs):
  return fetch_result
