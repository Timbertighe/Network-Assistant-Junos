"""
Connects to a Junos device and generate support files
    RSI, log collation
Uploads the files to an FTP server
Supports username and password for login to NETCONF over SSH
Junos supports RSA keys, but this script currently does not

Modules:
    3rd Party: JunosPyEz (junos-eznc), datetime, termcolor, threading
    Internal: core/teamschat, core/crypto, config.plugin_list

Classes:

    None

Functions

    get_logs()
        Extract details from the users request
    get_rsi()
        Collect logs from the device, and upload to FTP

Exceptions:

    None

Misc Variables:

    commands : list
        A list of show and request commands
        This is used when colleting extensive logs

Limitations:
    Requires NetConf to be enabled on the target device
    Uses username/password for authentication

Author:
    Luke Robertson - April 2023
"""


import datetime
import termcolor
import threading
from plugins.junos import netconf
import jnpr.junos.exception

from core import teamschat
from core import crypto
from config import plugin_list


# A list of commands to run
#   Used when getting extensive logs
commands = [
    ('request pfe execute command '
        '"show arena" target fwdd'),
    'show system storage',
    'show system virtual-memory',
    'show system processes extensive',
    'show security idp memory',
    'show chassis routing-engine',
    'show system processes extensive',
    'show services application-identification counter',
    'show security idp counters ips',
    'show security idp counters memory',
    'show security idp counters packet',
    'show security idp counters flow',
    'show security idp counters tcp-reassembler',
    'show security idp application-statistics',
    'show security flow session summary',
    'show security resource-manager summary',
    'show security resource-manager resource active',
    'show security resource-manager group active',
    'show services application-identification counter',
    'show services application-identification statistics applications',
    ('request pfe execute command '
        '"show arena" target fwdd'),
    ('request pfe execute command '
        '"show memory" target fwdd'),
    ('request pfe execute command '
        '"show heap 0" target fwdd'),
    ('request pfe execute command '
        '"show heap 1" target fwdd'),
    ('request pfe execute command '
        '"show heap" target fwdd'),
    ('request pfe execute command '
        '"show heap 0 sanity" target fwdd'),
    ('request pfe execute command '
        '"show heap 0 accounting pc" target fwdd'),
    ('request pfe execute command '
        '"show heap 0 accounting pc size" target fwdd'),
    ('request pfe execute command '
        '"show heap 1 accounting pc size" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm control objcache jsf summary" '
        'target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data objcache jsf summary" '
        'target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data module" target fwdd'),
    ('request pfe execute command '
        '"show usp memory-use all" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm control module" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm control objcache jsf" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data module" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment heap 0" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data objcache service" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data objcache jsf" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment heap modules" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment detail" target fwdd'),
    ('request pfe execute command '
        '"show usp idp status" target fwdd'),
    ('request pfe execute command '
        '"show usp idp context stats" target fwdd'),
    ('request pfe execute command '
        '"show usp idp context hits" target fwdd'),
    ('request pfe execute command '
        '"show usp idp memdebug" target fwdd'),
    ('request pfe execute command '
        '"show usp idp memory" target fwdd'),
    ('request pfe execute command '
        '"show usp idp debug-counter action" target fwdd'),
    ('request pfe execute command '
        '"show usp idp debug-counter memory" target fwdd'),
    ('request pfe execute command '
        '"show usp algs ftp stats" target fwdd'),
    ('request pfe execute command '
        '"show usp asl stats all" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf tcp stats" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf counters" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf counters junos-alg" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf flow stats" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf jbuf_pool stats" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf plugin-list" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf plugins" target fwdd'),
    ('request pfe execute command '
        '"show usp flow session summary" target fwdd'),
    ('request pfe execute command '
        '"show usp flow counters all" target fwdd'),
    ('request pfe execute command '
        '"show usp flow stats" target fwdd'),
    ('request pfe execute command '
        '"show usp flow counter all" target fwdd'),
    ('request pfe execute command '
        '"show usp gate all" target fwdd'),
    ('request pfe execute command '
        '"show usp gate statistics" target fwdd'),
    ('request pfe execute command '
        '"show usp appfw statistic" target fwdd'),
    ('request pfe execute command '
        '"show usp appfw counter" target fwdd'),
    ('request pfe execute command '
        '"show usp appid config" target fwdd'),
    ('request pfe execute command '
        '"show usp appid thread status" target fwdd'),
    ('request pfe execute command '
        '"show usp plugins" target fwdd'),
    ('request pfe execute command '
        '"show piles" target fwdd'),
    ('request pfe execute command '
        '"show mbuf host" target fwdd'),
    ('request pfe execute command '
        '"show mbuf counters" target fwdd'),
    ('request pfe execute command '
        '"show service objcache" target fwdd'),
    ('request pfe execute command '
        '"plugin jdpi show configuration tunables" target fwdd'),
    ('request pfe execute command '
        '"show jsf shm module" target fwdd'),
    ('request pfe execute command '
        '"show jsf objcache" target fwdd'),
    ('request pfe execute command '
        '"show jsf shm module" target fwdd'),
    ('request pfe execute command '
        '"show jsf objcache" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf counters" target fwdd'),
    ('request pfe execute command '
        '"show usp flow counters all" target fwdd'),
    ('request pfe execute command '
        '"show service objcache" target fwdd'),
    ('request pfe execute command '
        '"show jsf objcache" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment detail" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data objcache services" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data objcache jsf" target fwdd'),
    ('request pfe execute command '
        '"show piles" target fwdd'),
    ('request pfe execute command '
        '"show usp jsf jbuf_pool stats" target fwdd'),
    ('request pfe execute command '
        '"show usp memory segment shm data module" target fwdd')
]


def get_logs(chat_id, **kwargs):
    '''
    Extracts details from the users request, such as device name

    Parameters:
        chat_id : str
            The chat ID to report back to
        kwargs['ents'] : list
            A list of NLP entities
        kwargs['message'] : str
            The original message the user sent

    Returns:
        None
    '''

    # Look through kwargs to find a device name
    #   This should have an NLP entity of 'DEVICE' assigned
    device = ''
    if 'ents' in kwargs:
        for ent in kwargs['ents']:
            if ent['label'] == "DEVICE":
                device = ent['ent']
                break

    # If we have a valid device name:
    if device != '':
        teamschat.send_chat(
            f"I'll get the logs for {device}. Give me a few minutes",
            chat_id
        )

        # If we need extensive logging
        if 'extensive' in kwargs['message']:
            thread = threading.Thread(
                target=extensive_logs,
                args=(device, chat_id,)
            )

        # Regular logging
        else:
            thread = threading.Thread(
                target=get_rsi,
                args=(device, chat_id,)
            )

        # Start the thread
        thread.start()

    # If there's no valid device name, we can't proceed
    else:
        teamschat.send_chat(
            "Sorry. you'll need to give me a device name",
            chat_id
        )


def get_ftp(chat_id):
    '''
    Get FTP details to upload the logs

    (1) Get FTP server information
    (2) Get FTP username/password

    Parameters:
        chat_id : str
            The chat ID to report back to

    Returns:
        : dict
            The full FTP path (including username/password)
            A simplified path (no username/password)
        False : bool
            If there was a problem
    '''

    # Collect FTP server and directory information
    #   This comes from the config file
    ftp_server = ''
    ftp_dir = ''

    for plugin in plugin_list:
        if 'Junos' in plugin['name']:
            ftp_server = plugin['handler'].ftp_server
            ftp_dir = plugin['handler'].ftp_dir

    # Handle errors if this can't be found
    if ftp_server == '' or ftp_dir == '':
        print(termcolor.colored("Could not get FTP server details", "red"))
        teamschat.send_chat(
            "Sorry, I couldn't get the FTP server details from the plugin",
        )
        return False

    # Get passwords required to connect to the FTP server
    ftp_secret = crypto.pw_decrypt(dev_type='server', device=ftp_server)

    # If that didn't work, print an error and return
    if not ftp_secret:
        teamschat.send_chat(
            f"I couldn't get a password to connect to {ftp_server}",
            chat_id
        )
        return False

    # Build the FTP URL
    ftp_user = ftp_secret['user']
    ftp_pass = ftp_secret['password']
    ftp_url = f'ftp://{ftp_user}:{ftp_pass}@{ftp_server}/{ftp_dir}/'
    redacted = f'ftp://{ftp_server}/{ftp_dir}/'

    return {'full_path': ftp_url, 'redacted_path': redacted}


def get_rsi(host, chat_id):
    '''
    Connect to a junos device and get the logs

    (1) Generate the RSI
    (2) Compress logs to an archive
    (3) Upload to an FTP server

        Parameters:
            host : str
                The hostname to connect to
            chat_id : str
                The chat ID to report back to

        Returns:
            True : bool
                If successful
            False : bool
                If there was a problem
    '''

    # Get passwords required to connect to the device
    secret = crypto.pw_decrypt(dev_type='junos', device=host)
    if not secret:
        teamschat.send_chat(
            f"I couldn't get a password to connect to {host}",
            chat_id
        )
        return False

    # Connect to the Junos device; Should return a connection object
    # If the returned object is not right, handle the error
    dev = netconf.junos_connect(host, secret['user'], secret['password'])
    if not isinstance(dev, jnpr.junos.device.Device):
        netconf.error_handler(err=dev, dev=dev, chat_id=chat_id)
        return False

    # Get extra details for filenames
    hostname = dev.facts['hostname']
    date = str(datetime.date.today())
    time = str(datetime.datetime.now().strftime("%H%M"))
    rsi_filename = f'/var/log/RSI-Support-{hostname}-{date}-{time}.txt'
    print(termcolor.colored(f'RSI filename: {rsi_filename}', 'green'))

    # Generate the RSI (needs a large timeout)
    result = netconf.send_shell(
        f'request support information | save {rsi_filename}',
        dev,
        timeout=1800
    )

    if not isinstance(result, str):
        netconf.error_handler(err=result, dev=dev, chat_id=chat_id)
        return False

    teamschat.send_chat(
        f"I've created the RSI<br> \
            <span style=\"color:Yellow\">{rsi_filename}</span>",
        chat_id
    )

    # Create an archive of logs
    log_filename = f'/var/tmp/Support-{hostname}-{date}-{time}.tgz'
    print(termcolor.colored(f'Archive filename: {log_filename}', 'green'))

    result = netconf.send_shell(
        f'file archive compress source /var/log/* destination {log_filename}',
        dev
    )

    if not isinstance(result, str):
        netconf.error_handler(err=result, dev=dev, chat_id=chat_id)
        return False

    print(termcolor.colored(f"Device responded: {result}", "green"))

    teamschat.send_chat(
        f"I've created the log archive<br> \
            <span style=\"color:Yellow\">{log_filename}</span>",
        chat_id
    )

    # Upload the archive to an FTP server
    ftp = get_ftp(chat_id)

    # Check for a valid result, and build filenames
    if ftp:
        ftp_url = ftp['full_path']
        ftp_server = ftp['redacted_path']
        ftp_file = f'{ftp_server}Support-{hostname}-{date}-{time}.tgz'

    else:
        return False

    # Inform the user
    print(termcolor.colored(f'Uploading to {ftp_url}', 'green'))
    teamschat.send_chat(
        "I'm uploading the archive now...",
        chat_id
    )

    # Copy the archive to FTP
    #   Sometimes the junos device mangles this string,
    #   so it should be manually encoded as ASCII
    result = netconf.send_shell(
        (
            f'file copy {log_filename} {ftp_url}'
        ),
        dev
    )
    print(termcolor.colored(f"FTP result: {result}", "cyan"))

    if 'not' in result.lower():
        netconf.error_handler(err=result, dev=dev, chat_id=chat_id)
        return False

    # Gracefully close the device
    teamschat.send_chat(
        f"All done! The logs are here:<br> \
            <span style=\"color:Yellow\">{ftp_file}</span>",
        chat_id
    )
    dev.close()

    return True


def extensive_logs(host, chat_id):
    '''
    Connect to a junos device to get detailed logs

    This collects more logs than the get_rsi() function
    This is typically used for more extensive troubleshooting

    (1) Generate system logs

    Parameters:
        host : str
            The hostname to connect to
        chat_id : str
            The chat ID to report back to

    Returns:
        True : bool
            If successful
        False : bool
            If there was a problem
    '''

    print(termcolor.colored("Getting extensive logs (20-25 minutes)", "green"))
    teamschat.send_chat(
        ("Collecting extensive Junos logs. "
         "This many logs will take 20-25 minutes to collect"),
        chat_id
    )

    # Get regular logs
    get_rsi(host, chat_id)

    # Get passwords required to connect to the device
    secret = crypto.pw_decrypt(dev_type='junos', device=host)
    if not secret:
        teamschat.send_chat(
            f"I couldn't get a password to connect to {host}",
            chat_id
        )
        return False

    # Connect to the Junos device; Should return a connection object
    # If the returned object is not right, handle the error
    dev = netconf.junos_connect(host, secret['user'], secret['password'])
    if not isinstance(dev, jnpr.junos.device.Device):
        netconf.error_handler(err=dev, dev=dev, chat_id=chat_id)
        return False

    # Get extra details for filenames
    hostname = dev.facts['hostname']
    date = str(datetime.date.today())
    time = str(datetime.datetime.now().strftime("%H%M"))

    teamschat.send_chat(
        "Now to get all the show commands...",
        chat_id
    )

    # Create a new directory for the logs to go in
    netconf.send_shell(
        'file delete-directory /var/log/extensive recurse',
        dev
    )
    netconf.send_shell(
        'file make-directory /var/log/extensive',
        dev
    )

    # Generate a separate log file in /var/log/extensive for each command
    #   The command is inserted into the filename
    for command in commands:
        tidy_command = command.replace("\"", "")
        tidy_command = tidy_command.replace(" ", "_")
        filename = f'/var/log/extensive/{tidy_command}.txt'

        # Run the command, and write the results to the filename
        try:
            result = netconf.send_shell(f'{command} | save {filename}', dev)
        except Exception as err:
            print(termcolor.colored(
                f"Could not run {command} on {hostname}",
                "red"
            ))
            print(termcolor.colored(err, "red"))

        # Handle any errors
        if not isinstance(result, str):
            netconf.error_handler(err=result, dev=dev, chat_id=chat_id)
            return False

    # Create an archive of logs
    log_filename = f'/var/tmp/extensive_logs-{hostname}-{date}-{time}.tgz'
    print(termcolor.colored(f'Archive filename: {log_filename}', 'green'))
    teamschat.send_chat(
        f"Archving logs to {log_filename}",
        chat_id
    )

    result = netconf.send_shell(
        f'file archive compress source /var/log/* destination {log_filename}',
        dev
    )

    if not isinstance(result, str):
        netconf.error_handler(err=result, dev=dev, chat_id=chat_id)
        return False

    # Upload the archive to an FTP server
    ftp = get_ftp(chat_id)

    # Check for a valid result, and build filenames
    if ftp:
        ftp_url = ftp['full_path']
        ftp_server = ftp['redacted_path']
        ftp_file = f'{ftp_server}{log_filename}'

    else:
        return False

    # Copy the archive to FTP
    #   Sometimes the junos device mangles this string,
    #   so it should be manually encoded as ASCII
    result = netconf.send_shell(
        (
            f'file copy {log_filename} {ftp_url}'
        ),
        dev
    )
    print(termcolor.colored(f"FTP result: {result}", "cyan"))

    if 'not' in result.lower():
        netconf.error_handler(err=result, dev=dev, chat_id=chat_id)
        return False

    # Gracefully close the device
    print(termcolor.colored(f"Extensive logs are at {ftp_file}", "green"))
    teamschat.send_chat(
        f"You can find your logs at {ftp_file}",
        chat_id
    )
    dev.close()

    return True
