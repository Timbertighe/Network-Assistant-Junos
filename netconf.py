"""
Supporting functions to connect to a junos device

Usage:
    Call junos_connect() to connnect to a device
    Call send_shell() to send a shell command to a device

Authentication:
    Supports username and password for login to NETCONF over SSH
    Junos supports RSA keys, but this script currently does not

Restrictions:
    Requires JunosPyEZ to be installed
    Requres a username/password to connect
    Requires NetConf to be enabled on the target device

To Do:
    Update error_handler() to use teams chats

Author:
    Luke Robertson - February 2023
"""

import termcolor
from jnpr.junos import Device
from jnpr.junos.utils.start_shell import StartShell
import jnpr.junos.exception
from core import teamschat


# Connect to a Junos device
def junos_connect(host, user, password):
    try:
        dev = Device(host, user=user, password=password).open()
    except Exception as err:
        return err
    return (dev)


# Send shell commands to the device
# Take the command to run, as well as the shell object
def send_shell(cmd, dev):
    # Print the command we're going to run
    print(termcolor.colored(cmd, "yellow"))

    # Convert the raw junos command to something the API can work with
    command = f'cli -c \'{cmd}\''

    # Connect to the device shell (for sending CLI commands)
    try:
        shell = StartShell(dev, timeout=60)
        shell.open()
    except jnpr.junos.exception.ConnectError as err:
        print(termcolor.colored(
            'There was an error connecting to the Junos shell: ' + repr(err),
            "red"
        ))
        return err

    # Attempt the command
    try:
        output = shell.run(command)
    except Exception as err:
        print('An error has occurred')
        print('Sometimes a device will get busy and reject the attempt')
        return err

    # Cleanup the output before returning
    # Extract the actual message, and remove excessive blank lines
    out_text = output[1].replace(command, "")
    out_text = out_text.replace("\r\r\n", "")

    # Return the response from the device
    shell.close()
    return (out_text)


# Handle errors when they occur
def error_handler(err, dev, chat_id):
    if isinstance(err, str):
        if 'could not fetch local copy of file' in err:
            teamschat.send_chat(
                "Um... This is embarassing... \
                    I can't find the archive file to upload to FTP",
                chat_id
            )
            print(termcolor.colored(
                "Error, can't find the archive file to upload to FTP",
                'red'
            ))
        elif 'Not logged in' in err:
            teamschat.send_chat(
                "I can't believe this... I can't upload to FTP<br> \
                    looks like the credentials may be wrong",
                chat_id
            )
            print(termcolor.colored(
                "Error, can't upload to FTP, check your credentials",
                'red'
            ))

        else:
            # Tidy up the error string to send to Teams
            error_string = repr(err)
            error_string = error_string.replace("% '", "")
            error_string = error_string.replace("cli -c \"\'", "")
            error_string = error_string.replace("\'cli -c", "")
            error_string = error_string.replace("\"", "<br>")
            error_string = error_string.replace("\\r\\n\\r\\n", "<br>")
            error_string = error_string.replace("\\r\\n", "<br>")
            error = f'<span style=\"color:Red\">{error_string}</span>'

            teamschat.send_chat(
                f"I've hit a snag... I can't upload to FTP. \
                    Does this make sense to you?<br> \
                    {error}",
                chat_id
            )

            print(termcolor.colored(
                f"An error has occurred: {repr(err)}",
                'red'
            ))

        dev.close()

    elif isinstance(err, jnpr.junos.exception.ConnectRefusedError):
        teamschat.send_chat(
            "Sorry. It refused my connection. <br> \
                Check SSH settings, including acceptable ciphers. <br>",
            chat_id
        )

    elif isinstance(err, jnpr.junos.exception.ConnectTimeoutError):
        teamschat.send_chat(
            "Unfortunately, I didn't get a response<br> \
                Check that the hostname or IP address is correct. \
                Be sure this is a junos device, and NETCONF is enabled <br>\
                Could it be the firewall? Surely not...",
            chat_id
        )

    elif isinstance(err, jnpr.junos.exception.ConnectAuthError):
        teamschat.send_chat(
            "Wow. Rude. It has denied my authentication attempt<br> \
                Can you check that I have the right username and password?",
            chat_id
        )

    elif isinstance(err, jnpr.junos.exception.ConnectUnknownHostError):
        teamschat.send_chat(
            "Hmmm... That didn't work<br> \
                Are you sure you spelled the hostname correctly?",
            chat_id
        )

    elif isinstance(err, jnpr.junos.exception.ConnectError):
        teamschat.send_chat(
            f"It won't let me connect, and I'm not sure why. \
                Perhaps you know what this error means?<br> \
                <span style=\"color:Red\">{repr(err)}</span>",
            chat_id
        )

    else:
        teamschat.send_chat(
            f"It won't let me connect, and I'm not sure why. \
                Perhaps you know what this error means?<br> \
                <span style=\"color:Red\">{repr(err)}</span>",
            chat_id
        )
