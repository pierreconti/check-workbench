import pandas as pd
import json
import numpy as np
import aiohttp
from collections import OrderedDict

class CheckError(Exception):
  pass

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

async def query(params):
  # Use the API key to perform a query on the Check API.
  # Apply the GraphQL query in check.gql.
  team = params['team'].strip()
  key = params['key'].strip()
  host = params['host'].strip()
  query = {
    'query': """
query {
  team(slug: "${team}") {
    projects { edges { node {
      title
      project_medias { edges { node {
        user {
          id
          name
        }
        created_at
        report_type
        metadata
        last_status
        media {
          quote
          picture
          url
          embed
        }
        tags { edges { node {
          tag_text
        }}}
        tasks { edges { node {
          annotator {
            user {
              id
              name
            }
          }
          created_at
          label
          status
          first_response {
            annotator {
              user {
                id
                name
              }
            }
            created_at
            content
          }
          log { edges { node {
            annotation {
              annotator {
                user {
                  id
                  name
                }
              }
              created_at
              content
            }
            event_type
          }}}
        }}}
        comments: annotations(annotation_type: "comment") { edges { node {
          annotator {
            user {
              id
              name
            }
          }
          created_at
          content
        }}}
        log { edges { node {
          created_at
          user {
            id
          }
          event_type
        }}}
      }}}
    }}}
  }
}
    """.replace('${team}', team)
  }
  async with aiohttp.ClientSession(headers={ 'X-Check-Token': key }) as session:
    async with session.post(host + '/api/graphql', data=query) as response:
      json = await response.json()
      if (json.get('error')):
        raise CheckError(json['error'])
      if (json.get('errors')):
        raise CheckError(json['errors'][0]['message'])
      return json

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
    tasks['task_%(i)d_added_by' % { 'i': i+1 }] = format_user(task['node']['annotator']['user'], False)
    tasks['task_%(i)d_added_by_anon' % { 'i': i+1 }] = format_user(task['node']['annotator']['user'], True)
    if task['node']['first_response']:
      tasks['task_%(i)d_answer' % { 'i': i+1 }] = task_answer(task['node'])
      tasks['task_%(i)d_date_answered' % { 'i': i+1 }] = pd.Timestamp.fromtimestamp(int(media['node']['created_at']))
      tasks['task_%(i)d_answered_by' % { 'i': i+1 }] = format_user(task['node']['first_response']['annotator']['user'], False)
      tasks['task_%(i)d_answered_by_anon' % { 'i': i+1 }] = format_user(task['node']['first_response']['annotator']['user'], True)
  return tasks

def format_user(user, anonymize):
  return 'Anonymous' if anonymize else user['name']

def flatten(team):
  # Convert the GraphQL result to a Pandas DataFrame.
  df = []
  for project in team['data']['team']['projects']['edges']:
    for media in project['node']['project_medias']['edges']:
      metadata = json.loads(media['node']['metadata'])
      df.append(OrderedDict({
        'project': project['node']['title'],
        'title': metadata['title'],
        'added_by': format_user(media['node']['user'], False),
        'added_by_anon': format_user(media['node']['user'], True),
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
      }))
  return pd.DataFrame(df)

async def fetch(params, **kwargs):
  try:
    return flatten(await query(params))
  except Exception as err:
    return '%(ex)s: %(err)s' % { 'ex': err.__class__.__name__, 'err': str(err) }

def render(table, params, *, fetch_result, **kwargs):
  if fetch_result is None:
    return fetch_result
  if fetch_result.status == 'error':
    return fetch_result
  if fetch_result.dataframe.empty:
    return fetch_result

  columns = [c for c in list(fetch_result.dataframe) if c.endswith('_anon')]
  for c in columns:
    if params['anonymize']:
      del fetch_result.dataframe[c.replace('_anon', '')]
    else:
      del fetch_result.dataframe[c]
  return fetch_result
