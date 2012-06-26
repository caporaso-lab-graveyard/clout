#!/usr/bin/env bash
###############################################################################
#
# TODO comment me!
#
###############################################################################
starcluster -c config/starcluster_config start nightly_tests

# To have the next command work without getting prompted to accept the new
# host, you must have 'StrictHostKeyChecking no' in your SSH config.

#starcluster -c config/starcluster_config sshmaster -u ubuntu nightly_tests \
#    'source /home/ubuntu/qiime_software/activate.sh; \
#    python /home/ubuntu/qiime_software/qiime-1.5.0-release/tests/all_tests.py \
#    >& qiime_all_tests_output.txt'
starcluster -c config/starcluster_config sshmaster -u ubuntu nightly_tests \
    'echo OK >& qiime_all_tests_output.txt'

starcluster -c config/starcluster_config get -u ubuntu nightly_tests \
    /home/ubuntu/qiime_all_tests_output.txt .

# The second -c tells starcluster not to prompt us for termination
# confirmation.
starcluster -c config/starcluster_config terminate -c nightly_tests
email_test_results.py -i qiime_all_tests_output.txt -l config/recipients.txt \
    -s config/email_settings.txt -t QIIME
#rm qiime_all_tests_output.txt
