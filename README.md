# Network-Assistant-Junos
A Junos plugin for the network assistant

# Using the plugin
Plugins need to be added to the 'plugins' directory of the Network Assistant, each in their own folder.
Plugins are then enabled in the global configuration file

## Webhooks
### Enabling Webhooks
    This requires an agent on Junos devices
    Take the agent.py file, and deploy it to /var/db/scripts/event/ on each device that you want to monitor
    Enable python on the device with 'set system scripts language python3'
    Add configuration to event-options to call scripts when certain system events occur. For example:
    
```Junos
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
```

    It is not recommended to alert on these events, as they are cosmetic, and cause too much noise:
        * UTMD_EWF_CAT_OBSOLETE
        * RPD_RT_HWM_NOTICE
        
### Webhook Authentication
    Junos authentication uses HMAC-SHA-256
    It adds a 'Junos-Auth' header, containing a hash of the body and the secret
    
### Device Resources
    Junos devices have limited resources, and multiple scripts (or instances of a script) can run at once
    This can lead to a 'Junos policies exceeding limit' message in the system logs on the device
    This just means that there is a limit to how many scripts can run concurrently. Typically this is 15.
    This delays the running of a script until this is back below the limit. This prevents the device from being overwhelmed by script processing

## Device Interaction
    This plugin supports sending requests to device through NETCONF

### Device Authentication
    When sending commands to devices, the chatbot needs to be authenticated
    Usernames and passwords are stored in the secrets.yaml file
    The authentication 'type' for logging on to devices is assumed to be 'junos'
    The authentication 'type' for logging on to an FTP server is assumed to be 'server'
    
### Get Logs
    The jtac-logs.py file has functions to build an RSI file, archive logs, and upload to FTP
    This is always required by JTAC when logging a ticket
    
### Reboot Devices
    The reboot.py file has functions to get user NLP phrases, and determine when to reboot a device (or devices)
    
### Restart processes
    The restart-proc.py file has functions to get NLP phrases, and restart a process on a given device


## Configuration
### Overview
    Plugin configuration is in the 'junos-config.yaml' file
    the 'events' section can be used to assign priority levels and filter events
    
#### Plugin Config
    Set 'webhook_secret' to the secret, as set in the junos event-options configuration
    Set the 'auth_header' to Junos-Auth; This is how the main program knows which header to check for authentication



&nbsp;<br>
- - - -
## Files
### sql-create.py
    A standalone script that connects to the SQL server, as globally defined in the app
    Created the table and fields
    
    
&nbsp;<br>
### agent.py
    A standalone script that is deployed on Junos devices
    Junos devices are configured to call this script on particular events
    This script will then collect the necessary details, and send them as a webhook


&nbsp;<br>
### junos-config.yaml
    A YAML file that contains all the config for the junos plugin
    This includes:
        * webhook_secret - The secret we expect to see from the device sending the webhook
        * auth_header - The header we expect to see in the webhook message
        * sql_table - The SQL table name that the plugin will write events to
        * chat_id - The chat ID to send alerts to
        * ftp_server - The FTP server to (optionally) upload files to
        * ftp_dir - The FTP directory to use on the FTP server
    There are a list of known events
        These include a priority number (1-4) which determines how important the alert is
        1 - Log, and send to teams (with detail)
        2 - Log, and send to teams (summary)
        3 - Log to SQL only
        4 - Ignore completely


&nbsp;<br>
### junos.py
    The JunosHandler class that handles events as they are received
    
#### __init__()
    Loads the config file
    
#### handle_event(raw_response, src)
    Handles a webhook when it arrives
        'raw_response' is the raw webhook
        'src' is the IP that sent the webhook
    Sends the event to alert_priority() to assign a priority
    Prepares a message to send to teams
    Sends the message and event to log()
    
#### alert_priority()
    Assigns a priority to each alert, to affect how its handled

#### log()
    Sends the message to teams (if needed)
    Prints the event to the terminal
    Writes the event to SQL

#### refresh()
    Rereads the config
    This allows config changes to be made without restarting Flask

### agent.py
    The agent script that is added to the Junos devices
    This is passed an event from 'event-options'
    This will send the event as a webhook to the chatbot
    
### netconf.py
    Enables communication with Junos devices over NETCONF
    The NETCONF protocol needs to be enabled on the device
    
#### junos_connect()
    Connects to a junost device
    Takes a hostname, username, and password
    Returns a connection object if successful

#### send_shell()
    Sends shell commands to the device
    Takes the command to run (as a string) and a connection object)
    Creates a shell object, sends the command, and returns the result if successful
    Sends to error_handler() if there was a problem

#### error_handler()
    Handles any errors that occurred
    Takes an error, a connection object, and a chat_id
    Sends error messages to teams
    Writes error messages to the terminal
    

&nbsp;<br>
### netconf.py
    Supporting functions to connect to a Junos device
    Requires the JunosPyEZ library to be installed
    Requires NETCONF to be enabled on the target device
    
#### junos_connect()
    Arguments:
        host - The host device to connect to
        user - The username to authenticate with
        password - The password to authenticate with
    Returns:
        dev - A JunosPyEz device object, describing the connection to the device
    Purpose:
        Connect to a device, authenticate, and create a device connection object

#### send_shell()
    Arguments:
        cmd - The junos command to send to the device
        dev - A device connection object
    Returns:
        err - An exception object, if an error occurred
        our_text - The output text from running the command on the device
            Note, this does not necessarily mean the command worked as desired
            This means that the command was accepted and run
    Purpose:
        Need to have connected to the device first (with junos_connect), and have the connection object
        Gives the device Junos commands to run

#### error_handler()
    Arguments:
        err - An exception object, describing the error
        dev - A device connection object
        chat_id - The Teams chat ID to send the error to
    Returns:
        None
    Purpose:
        Deciphers the meaning of an exception object, and sends it to teams
        Closes the connection to the device on completion


&nbsp;<br>
### jtac-logs.py
    Collects RSI and other logs for use by JTAC
    
#### get_logs()
    Arguments:
        chat_id - The chat ID to send messages to
        **kwargs - Optional list of extra entities (device names)
    Returns:
        None
    Purpose:
        Give immediate feedback to the user
        Gets a device name to get logs for
        Start a thread that calls get_rsi()
    
#### get_rsi()
    Arguments:
        host - The Junos host to connect to
        chat_id - The chat ID to send messages to
    Returns:
        None
    Purpose:
        Get the username/password for the device using secrets.yaml and crypto.py
        Connect to the junos device using functions in netconf.py
        Get the device hostname using JunosPyEz 'facts'
        Generate the RSI file, and inform the user
        Add the RSI and other logs to an archive, and inform the user
        Upload the archive to the FTP location (in the config file), and inform the user
        Gracefully close the connection to the device


&nbsp;<br>
### reboot.py
    Takes a phrase from a user, and uses this to reboot a device immediately, or a relative/absolute time
    
#### reboot()
    Arguments:
        'device' - The device name to reboot
        'user' - The username to log on with
        'password' - The password to log on with
        'chat_id' - The chat ID to provide feedback to
        **kwargs - Optional details:
            'time' - A date/time to reboot the device (a datetime object)
            'duration' - A time (in minutes) to reboot the device
    Returns:
        None
    Purpose:
        Takes the given details, and reboots a device
        Connects to the given device name, using the given credentials
        If 'time' or 'duration' is not provided, the device will be rebooted immediately
        If 'time' is given, the reboot is scheduled for that time
        if 'duration' is given, the reboot is deferred for that many minutes
        Will inform the user on teams if another reboot or shutdown has been scheduled

#### nlp_reboot()
    Arguments:
        'chat_id' - The teams chat to provide feedback to
        **kwargs - Optional NLP entities that provide the function more information
    Returns:
        None
    Purpose:
        Takes a phrase from the user, requesting a reboot
        Finds the device name to reboot; More than one is fine
        Finds the username/password to connect to the device
        If there are no additional parameters, reboot() is called to reboot the device(s) immediately
        If there are additional parameters, it will work out a relative or absolute time, and pass this to reboot()
        The reboot() function is run as a separate thread
    
    
&nbsp;<br>
### junos.py
    Takes a phrase from a user, and uses this to restart a process on a device gracefully or immediately

#### restart()
    Arguments:
        'device' - The device name to reboot
        'user' - The username to log on with
        'password' - The password to log on with
        'process' - The process to restart
        **kwargs - Optional details:
            'immediately' - Set to True to immediately restart the process (SIGKILL)
    Returns:
        None
    Purpose:
        Takes the given details, and restarts a process on a device
        Connects to the given device name, using the given credentials
        Restarts the given process


#### nlp_restart()
    Arguments:
        'chat_id' - The teams chat to provide feedback to
        **kwargs - Optional NLP entities that provide the function more information
    Returns:
        None
    Purpose:
        Takes a phrase from the user, requesting a restart of a process
        Finds the device name to connect to; More than one is fine
        Finds the username/password to connect to the device
        Determines the name of the process to restart
        The restart() function is run as a separate thread


