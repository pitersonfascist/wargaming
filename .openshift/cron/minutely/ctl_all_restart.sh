#!/bin/bash
#Configure your Openshift SSH username
sshid='540f50ee5973ca056000034c'
  
#Running the script, for your own applications
curl -I warg-piterson.rhcloud.com 2> /dev/null | head -1 | grep -q '200\|302'

s=$?

if [ $s != 0 ];
    then
        echo "`date +"%Y-%m-%d %I:%M:%S"` down" >> /var/lib/openshift/$sshid/app-root/data/web_error.log
        #%10 take more than a minute
        let t=`date +"%M"`%10
        #Every 10 minutes a time, to prevent the continuous restart several times, the server too much pressure
        if [ $t -eq 0 ];
            then
                #Restart the log superposition record > >, found that is too large can be deleted, or changed to cover the record>
                echo "`date +"%Y-%m-%d %I:%M:%S"` restarting..." >> /var/lib/openshift/$sshid/app-root/data/web_error.log
                /usr/bin/gear stop 2>&1 /dev/null
                /usr/bin/gear start 2>&1 /dev/null
                echo "`date +"%Y-%m-%d %I:%M:%S"` restarted!!!" >> /var/lib/openshift/$sshid/app-root/data/web_error.log
        fi
else
    echo "`date +"%Y-%m-%d %I:%M:%S"` is ok" > /var/lib/openshift/$sshid/app-root/data/web_run.log
fi
 
