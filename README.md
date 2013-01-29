![Clout logo](https://raw.github.com/qiime/clout/master/resources/clout_logo.png "Clout: Cloud-based Automated Testing")

# Clout: Cloud-based Automated Testing

_clout_ is a tool that facilitates the automated testing of software using Amazon's EC2 service as a testing platform. _clout_ can work with any number of testing suites and programming languages.

_clout_ is currently being used to test the following bioinformatics projects on a nightly basis (in addition to testing itself):

* [QIIME](http://qiime.org/)
* [PyCogent](http://pycogent.org/)
* [biom-format](http://biom-format.org/)
* [PICRUSt](http://picrust.github.com/picrust/)
* [Primer Prospector](http://pprospector.sourceforge.net/)
* [PyNAST](http://qiime.org/pynast/)

If you are using _clout_ to test your software, we'd love to hear from you and add your project to the list!

Please refer to the ```INSTALL.md``` file for details on how to install and set up _clout_ to run your test suites.

## What is Clout and how does it work?

_clout_ is a tool that executes any number of test suites using Amazon's EC2 service and emails the results to a list of recipients. [StarCluster](http://star.mit.edu/cluster/) is used to boot up a cluster on EC2 and the test suites are executed on the cluster. This has the advantage of freeing up locally-maintained systems from running computationally-intensive processes, allowing the heavy work to be done on Amazon's always-available and reliable EC2 service. The type of compute node that the tests are run on is also configurable, which makes _clout_ flexible and scalable to project of any size, allowing you to choose the right hardware for the timely execution of your test suites.

_clout_ is designed to be used in a command scheduler program (such as _cron_) in order to automatically execute a suite of tests and email the results to a list of recipients. Thus, you will only interact with a single executable (aptly named ```clout```) to set up, run your test suites, and email the results. This script can be easily added to a crontab so that you can receive test suite results on a regular basis (e.g. nightly).

## Input Configuration Files

_clout_ requires four different configuration files as input. Examples of each
type of file can be found under the ```templates/``` directory.

### Test suite configuration file

This file contains tab-separated fields describing each test suite that will be run by _clout_. All fields are required. The test suites will be executed in the order that they appear in this file.

The first field is the label/name of the test suite, as it will appear in the email summary. This field can be virtually any human-readable string that will be used to identify the test suite. This field must be unique across all entries in this file.

The second field is the set of commands that will be executed to run the test suite on the cluster. This includes any setup commands (e.g. sourcing a shell script, svn updating a checkout to ensure you're testing the latest and greatest changes, etc.) that need to be run before the test suite is executed.  All stdout and stderr will be logged for these commands and included in the email. It is recommended that you use absolute paths for all of the filepaths.  It is also recommended to use '&&' to separate multiple commands so that the commands will abort at the first failure and return that exit code instead of trying to continue on. This way you'll be able to see the first thing that failed and not waste money paying for EC2 compute power that ultimately won't prove useful.

**NOTE:** The commands that are executed should follow the Unix standard for return codes (a return code of zero indicates success, anything else indicates failure). _clout_ uses the return codes to determine whether or not there was a problem in executing any of the commands, as well as to determine the status of the test suites themselves. Thus, if a test fails, make sure your test suite executable returns a non-zero return code, and likewise, if all tests pass, your test suite executable should return zero for success.

### StarCluster configuration file

This file is the StarCluster configuration file that _clout_ will use when booting up a cluster. This file contains important information regarding your Amazon EC2 account, the cluster template to use for running the tests on, etc.. Please refer to the [StarCluster website](http://web.mit.edu/star/cluster/) for instructions on how to set up a StarCluster configuration file.

**NOTE:** _clout_ currently only uses a single master node on the cluster to execute the test suites on (the test suites are executed one after another). Thus, you'll only need a single-node cluster defined in your cluster template (see the example config file for more details).

**TIP:** Make sure the RSA key that this config file points to is in the correct location and has the right permissions (e.g. ```chmod 400 key.rsa```).

### Email recipients configuration file

This file contains a list of email addresses (one per line) of the individuals who should receive an email of the testing results.

### Email settings configuration file

This file contains four key/value pairs (each separated by a tab) that define how _clout_ should send the email. The fields ```smtp_server```, ```smtp_port```, ```sender```, and ```password``` must be defined. The ```sender``` field is the email address that will show up in the _From_ field in the email, and it is also used to log into the SMTP server in conjunction with the ```password``` field.

## Usage Examples

**Example 1:** Execute unit test suites remotely

Executes the unit test suites defined in the input configuration file as the ```ubuntu``` user and emails the test results to everyone in the provided email list. The default StarCluster template is used (as is defined in the input starcluster config file) and the starcluster cluster tag is ```nightly_tests```.

    clout -i templates/test_suite_config.txt -s templates/starcluster_config -u ubuntu -c nightly_tests -l templates/recipients.txt -e templates/email_settings.txt

**Example 2:** Execute test suites remotely using a custom StarCluster cluster template

Executes the test suites using a custom StarCluster cluster template ```test-cluster``` instead of the default cluster template in the StarCluster config file.

    clout -i templates/test_suite_config.txt -s templates/starcluster_config -u ubuntu -c nightly_tests -l templates/recipients.txt -e templates/email_settings.txt -t test-cluster

## Acknowledgements

_clout_ was developed by Jai Ram Rideout ([@jrrideout](https://github.com/jrrideout)) in the [Caporaso Lab](http://www.caporaso.us) at Northern Arizona University. Development was supported by an [Amazon Web Services in Education researcher's grant](http://aws.amazon.com/education/) to the [QIIME](http://www.qiime.org) development group. _clout_ is powered by [StarCluster](http://star.mit.edu/cluster/).
