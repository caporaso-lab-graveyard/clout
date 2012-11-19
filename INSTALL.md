# Clout Installation Guide

## Required Dependencies

_clout_ requires:

* Python 2.7 (other versions may also work, though this is the officially tested and supported version)
* StarCluster (tested on version 0.93.3)

## System Setup

Edit your ssh config (typically in ~/.ssh/config) and add the following two lines:

    StrictHostKeyChecking no
    ServerAliveInterval 120

The first line tells SSH not to ask us whether we want to connect or not to an unknown host, which will ALWAYS occur since the Amazon EC2 instance will always be a new host each time one is created. This option allows us bypass this prompt and keep the entire process automated.

The second line tells us to send keepalive packets to the Amazon EC2 instance every two minutes so that our SSH connection doesn't drop during long-running test suites.

Add _clout_'s scripts and library areas to your ```PATH``` and ```PYTHONPATH```, respectively, changing the filepaths to point to wherever this project resides. Feel free to add these lines to your .bashrc or .bash_profile so that you won't have to execute them every time you open a new shell (make sure to source your .bashrc or .bash_profile after you've added the lines):

    export PATH=/home/some_user/clout/scripts:$PATH
    export PYTHONPATH=/home/some_user/clout:$PYTHONPATH

Test that your install appears to be working by running the following command:

    clout -h

You should see _clout_'s help text printed to your terminal.

## Cron Job Setup

You may want to add the ```clout``` executable to a crontab to have your test suites automatically run at some regular time interval. To do so, you'll need to set the ```PYTHONPATH``` from within the crontab to tell Python where to look for _clout_'s library code. You'll also need to add the directories where Python and StarCluster reside to the ```PATH``` variable within the crontab, or run the script specifying the full path to your Python executable, and use the ```--starcluster_exe_fp``` option to ```clout``` to specify the full path to StarCluster.

Edit your crontab with the following command:

    crontab -e

Add the following lines to the crontab, if you'd like to use environment
variables to locate Python and StarCluster:

    PATH=/path/to/starcluster/executable/directory
    PYTHONPATH=/path/to/clout/directory

For example, if Python is in /usr/bin and StarCluster is in /usr/local/bin:

    PATH=/usr/bin:/usr/local/bin
    PYTHONPATH=/home/ubuntu/clout

Please be sure to use absolute paths for all filepaths and commands in the crontab.

Alternatively, you can remove the ```PATH``` line altogether by running the ```clout``` command like so in your crontab (using full paths to avoid having to set ```PATH```):

    /usr/bin/python /home/ubuntu/clout/scripts/clout -i <...> --starcluster_exe_fp /usr/local/bin/starcluster

There are various ways to set up your system to receive email from the cron job if the script produces any output (e.g. if it raises an error). If the script runs normally, there shouldn't be any output (stdout or stderr), but it is a good idea to make sure that someone will receive emails from the cron system if something goes wrong. [This website](https://wiki.archlinux.org/index.php/SSMTP#Forward_to_a_Gmail_Mail_Server) has an excellent guide to setting up your system to forward emails to an external SMTP server (they show how to set it up for an external Gmail account). This was verified to work on an Amazon EC2 instance that was running the cron job.
