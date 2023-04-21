"""
Reboot a juniper device
Immediately, in a given time, or at a given time

Usage:
    TBA

Authentication:
    Supports username and password for login to NETCONF over SSH
    Junos supports RSA keys, but this script currently does not

Restrictions:
    Requires JunosPyEZ to be installed
    Requres a username/password to connect
    Requires NETCONF to be enabled on the target device
    Requires dateutil (pip install python-dateutil)

To Do:
    TBA

Author:
    Luke Robertson - March 2023
"""

# 'SW' is the 'Software Utility' class
# This is used for upgrades, file copies, reboots, etc
from jnpr.junos import Device
from jnpr.junos.utils.sw import SW
from jnpr.junos.exception import ConnectError
from jnpr.junos.exception import RpcError

from datetime import datetime, timedelta
from dateutil.parser import parse
from core import crypto
from core import teamschat
import threading


# Reboot a device under various conditions
#   Now, in a particular time, at a particular time
# This is a function built into the junosPyEz library
#   We don't need to keep connection objects and send CLI commands
def reboot(device, user, password, chat_id, **kwargs):
    '''
    Reboots a Junos device
    'time' parameter (datetime object) - Reboot at a time
    'duration' parameter (positive integer) - Reboot in a given time (minutes)
    No parameter - Reboot immediately
    '''

    print(f"Connecting to {device}...")

    # Connect to the device
    try:
        with Device(host=device, user=user, passwd=password) as dev:
            # Instantiate the 'Software Utility' class
            try:
                sw = SW(dev)
            except Exception as err:
                print("Could not create the software class")
                print(err)
                return

            # If there are no parameters, reboot now
            if kwargs == {}:
                print("Rebooting now")
                result = sw.reboot()

            # If the 'time' parameter is present, reboot then
            elif 'time' in kwargs:
                if kwargs['time'] < datetime.now():
                    print("This time is in the past")
                    return

                print(f"Rebooting at {kwargs['time']}")
                # Convert the time to a format junos uses
                junos_format = kwargs['time'].strftime("%y%m%d%H%M")
                result = sw.reboot(at=junos_format)

            # If the 'duration' parameter is present,
            # reboot in that many minutes
            elif 'duration' in kwargs:
                if kwargs['duration'] < 1 or type(kwargs['duration']) != int:
                    print("This needs to be a positive whole integer")
                    return

                print(f"Rebooting in: {kwargs['duration']} minutes")
                result = sw.reboot(in_min=kwargs['duration'])

            # If there are parameters, but not 'time' or 'duration',
            # there is an error
            else:
                print("You have used invalid parameters")
                print("  Pass no parameters to reboot now")
                print("  Pass 'time' parameter to reboot at a particular time")
                print("  Pass 'duration' to reboot in a number of minutes")

            print(result)
            teamschat.send_chat(
                f"{device}: {result}",
                chat_id
            )

    # Handle Connection error
    except ConnectError as err:
        print(f"There has been a connection error: {err}")
        teamschat.send_chat(
            f"There was a problem connecting to {device}",
            chat_id
        )

    # Handle an RPC error
    except RpcError as err:
        if 'another shutdown is running' in str(err):
            print("Unable to reboot")
            print("Another reboot/shutdown has been scheduled")
            teamschat.send_chat(
                "Unable to reboot, as another reboot is scheduled",
                chat_id
            )

        else:
            print(f"RPC Error has occurred: {err}")

    # Handle a generic error
    except Exception as err:
        print(f"Error was: {err}")


# Use NLP to parse the message, and handle the reboot
def nlp_reboot(chat_id, **kwargs):
    # Find one or more device names in the entities
    device_list = []
    if 'ents' in kwargs:
        for ent in kwargs['ents']:
            if ent['label'] == "DEVICE":
                device_list.append(ent['ent'])

    # At the very least, we need one device to reboot
    if len(device_list) == 0:
        print("You need to give me a device name")
        return

    # See if a time is included
    time = ''
    for ent in kwargs['ents']:
        if ent['label'] == 'TIME':
            time = ent['ent']
            break

    # Check if a date is involved (eg, tomorrow)
    date = ''
    for ent in kwargs['ents']:
        if ent['label'] == 'DATE':
            date = ent['ent'].lower()
            break

    # If not, reboot now
    if time == '' and date == '':
        for device in device_list:
            print(f"Reboot requested for {device}")
            secret = crypto.pw_decrypt(dev_type='junos', device=device)
            if not secret:
                print("Could not get credentials")
                return False
            thread = threading.Thread(
                target=reboot,
                kwargs={
                    'device': device,
                    'user': secret['user'],
                    'password': secret['password'],
                    'chat_id': chat_id
                }
            )
            thread.start()

            teamschat.send_chat(
                f"Reboot requested for {device}",
                chat_id
            )

        return

    # If the reboot should happen in a relative time from now
    if 'seconds' in time or \
       'minutes' in time or \
       'hours' in time or \
       'days' in time:
        time_value = int(time.split()[0])
        time_units = time.split()[1]

        match time_units:
            case "minutes" | "minute":
                pass
            case "hours" | "hour":
                time_value = time_value * 60
            case "seconds | second":
                time_value = int(time_value / 60)
            case "days" | "day":
                time_value = time_value * 1440
            case _:
                print(f"{time_units} is not a valid unit of time")
                return

        for device in device_list:
            secret = crypto.pw_decrypt(dev_type='junos', device=device)
            if not secret:
                print("Could not get credentials")
                return False
            thread = threading.Thread(
                target=reboot,
                kwargs={
                    'device': device,
                    'user': secret['user'],
                    'password': secret['password'],
                    'chat_id': chat_id,
                    'duration': time_value
                }
            )
            thread.start()

            teamschat.send_chat(
                f"Rebooting {device} in {time_value} minutes",
                chat_id
            )
            print(f"Rebooting {device} in {time_value} minutes")

    # If the reboot should happen at an absolute time
    else:
        # Attempt to parse the time into something recognisable
        try:
            dt = parse(time)
        except Exception as err:
            print(f"I'm not sure what {time} means")
            print(err)

        # If this turns out to be a time in the past, add 1 day
        # If 'tomorrow' used, add 1 day
        if dt < datetime.now() or date == 'tomorrow':
            dt = dt + timedelta(days=1)

        # Execute the reboot
        for device in device_list:
            print(f"Rebooting {device} at {dt}")
            secret = crypto.pw_decrypt(dev_type='junos', device=device)
            if not secret:
                print("Could not get credentials")
                return False
            thread = threading.Thread(
                target=reboot,
                kwargs={
                    'device': device,
                    'user': secret['user'],
                    'password': secret['password'],
                    'chat_id': chat_id,
                    'time': dt
                }
            )
            thread.start()

            teamschat.send_chat(
                f"Rebooting {device} at {dt}",
                chat_id
            )

    return
