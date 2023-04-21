'''
[edit system]
scripts {
    language python3;
}

[edit event-options]
policy Webhooks {
    events LICENSE_EXPIRED_KEY_DELETED;
    then {
        event-script junos-agent.py {
            arguments {
                url <DESTINATION>;          <<< The URL to send webhooks to
                secret <SECRET>;            <<< The webhooks secret
            }
        }
    }
}
event-script {
    file junos-agent.py {
        python-script-user admin;
        checksum sha-256 xxxx;              <<< use 'file checksum sha-256 FILENAME' to get the checksum of this file
    }
}

https://www.juniper.net/documentation/us/en/software/junos/automation-scripting/topics/concept/junos-script-automation-event-script-input.html


Assumes junos 21.2R1 and later

'''


import requests
import json
import argparse
import hmac
import hashlib

from junos import Junos_Trigger_Event
from jnpr.junos import Device


# Collect top 4 CPU users
def top():
    with Device() as jdev:
        cmd1 = jdev.cli('show system processes extensive')

    full_list = cmd1.split("\n")
    proc_list = []
    top_counter = 0

    # Use a range to skip the summary at the beginning
    for item in full_list[9:-1]:
        if ('0.00%' not in item) and ('flowd_octeon_hm' not in item):
            # Only collect the top 4 processes (by CPU)
            if top_counter >= 4:
                break

            # Cleanup the data before working with it
            item = item.strip()
            item = item.split()

            # Sometimes the command has a space in it
            # Convert this back into a string
            if len(item) > 11:
                item[10] = f"{item[10]} {item[11]}"

            # Save the relevant details as a dictionary
            # Save the cpu as a float, not a string
            proc = {
                'pid': item[0],
                'user': item[1],
                'cpu': float(item[9].replace("%", "")),
                'command': item[10]
            }
            proc_list.append(proc)
            top_counter += 1

    return proc_list


# Create a hash, using the body of the request, and a secret
def create_hash(body, secret):
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


# Setup arguments
helpmsg = "Junos webhooks agent"
parser = argparse.ArgumentParser(description=helpmsg)

parser.add_argument("-url", help="URL to send webhooks to")
parser.add_argument("-secret", help="URL to send webhooks to")
args = parser.parse_args()


# Data to send
data = {
    'event': Junos_Trigger_Event.xpath('//trigger-event/id')[0].text,
    'process': Junos_Trigger_Event.xpath('//trigger-event/process/name')[0].text,
    'message': Junos_Trigger_Event.xpath('//trigger-event/message')[0].text,
    'hostname': Junos_Trigger_Event.xpath('//trigger-event/hostname')[0].text,
    'detail': ''
}

# Add special handling, depending on the event
if 'RTPERF_CPU' in data['event']:
    data['detail'] = top()

body = json.dumps(data)
auth_header = create_hash(body, args.secret)


# Send information as a webhook
try:
    req = requests.post(
        args.url,
        data=body,
        headers={
            'Content-type': 'application/json',
            'Junos-Auth': auth_header
        }
    )
except Exception as err:
    print("Error occurred sending the webhook")
    print(err)
