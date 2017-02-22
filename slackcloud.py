#! /usr/bin/env python

import os
import logging
import threading

import matplotlib.pyplot as plt
from flask import Flask
from flask_slack import Slack
from slacker import Slacker
from wordcloud import WordCloud


app = Flask(__name__)

# Used for flask_slack @slack.command helper
slack = Slack(app)
app.add_url_rule('/', view_func=slack.dispatch)

# Change log level to increase or decrease verbosity
logging.basicConfig(level=logging.INFO)

# Load up custom Slack environment variables
slack_auth = os.environ.get('SLACK_AUTH')
slack_teamid = os.environ.get('SLACK_TEAMID')
slack_cmd1_name = os.environ.get('SLACK_CMD1_NAME')
slack_cmd1_token = os.environ.get('SLACK_CMD1_TOKEN')
port = int(os.environ.get("PORT", 8081))

def extract_messages(messages):
    msgs = []
    latestts = None
    oldestts = None

    for i in range(len(messages)):
        if messages[i]['type'] == 'message':
            try:
                subtype = messages[i]['subtype']
            except:
                msgs.append(messages[i]['text'])

        if i == 0:
            latestts = messages[i]['ts']

        if i == len(messages) - 1:
            oldestts = messages[i]['ts']

    return msgs, latestts, oldestts

def upload_wordcloud(channel_id, channel_name, **kwargs):
    slack = Slacker(slack_auth)

    msgs = []
    latestts = None
    oldestts = None
    hasMore = True

    while hasMore:
        if latestts is None:
            result = slack.channels.history(channel_id, None, None, 1000)
        else:
            result = slack.channels.history(channel_id, latestts, oldestts, 1000)

        if result.body['has_more'] != "true":
            hasMore = False

        messages, latestts, oldestts = extract_messages(result.body['messages'])
        msgs.extend(messages)

        if not hasMore:
            break
        
        print 'has more'

    logging.debug(msgs)
    try:
        # Concat all the words
        text = ' '.join(msgs)
        wordcloud = WordCloud().generate(text)
        plt.imshow(wordcloud)
        plt.axis("off")
        plt.savefig('/tmp/' + channel_name)
        initial_comment = 'Requested by {}'.format(kwargs.get('user_name'))
        slack.files.upload('/tmp/' + channel_name + '.png',
                           channels=channel_id,
                           initial_comment=initial_comment)
    except TypeError as e:
        logging.error(e)

@slack.command(command=slack_cmd1_name, token=slack_cmd1_token,
               team_id=slack_teamid, methods=['POST'])
def parse_slash_cmd(**kwargs):
    ch_id = kwargs.get('channel_id')
    ch_name = kwargs.get('channel_name')
    user_id = kwargs.get('user_id')
    user_name = kwargs.get('user_name')
    wcloud = threading.Thread(target=upload_wordcloud,
                              args=(ch_id, ch_name),
                              kwargs={'user_name': user_name})
    wcloud.start()
    return slack.response('Enjoy your wordcloud!')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port)
