automated_testing
=================

Automated testing system for development versions of QIIME, PyCogent, biom-format, and more.

This system executes any number of test suites using Amazon's EC2 service and
emails the results to a predefined list of recipients. StarCluster is used to
boot up a cluster on the EC2 and the test suites are executed on the cluster.
This has the advantage of freeing up locally-maintained systems from running
computationally-intensive processes, allowing the heavy work to be done on
Amazon's always-available and reliable EC2 service. The type of compute node
that the tests are run on is also configurable, which has the advantage of
flexibility and scalability, allowing you to easily choose the right hardware
for the timely execution of your test suites.

This system is designed to be used in a command scheduler program (such as
cron) in order to automatically execute a suite of unit tests and email the
results to a list of recipients. Thus, you will only interact with a single
script (run_test_suites.py) to set up, run your test suites, and email the
results. This script can be easily added to a crontab so that you can receive
test suite results every night, for example.

Please refer to the INSTALL file for details on how to set up the system.
