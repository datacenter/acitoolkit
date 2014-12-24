.. _egrDropPkts-label:

egrDropPkts
---------------------------

================  ==========  =================================================================
Name              Type        | Description 
================  ==========  =================================================================
afdWredAvg        integer     | **Egress packets dropped due to AFD or WRED**. 
                              | This is a count of the packets dropped due to whichever active 
                              | queue managment mechanism is running in the switch, either AFD 
                              | or WRED. This is the average value read by the counter during 
                              | the collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
afdWredCum        integer     | **Egress packets dropped cumulative due to AFD or WRED**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
afdWredMax        integer     | **Egress packets dropped by AFD or WRED maximum value read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
afdWredMin        integer     | **Egress packets dropped by AFD or WRED minimum value read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
afdWredPer        integer     | **Egress packets dropped by AFD or WRED per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
afdWredRate       float       | **Egress packets dropped by AFD or WRED rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
bufferAvg         integer     | **Egress packets dropped due to buffer full**. 
                              | This is the average value read by the counter during the 
                              | collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
bufferCum         integer     | **Egress packets dropped cumulative due to buffer full**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
bufferMax         integer     | **Egress packets dropped due to buffer full maximum read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
bufferMin         integer     | **Egress packets dropped due to buffer full minimum read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
bufferPer         integer     | **Egress packets dropped due to buffer full per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
bufferRate        float       | **Egress packets dropped due to buffer full rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
errorAvg          integer     | **Egress packets dropped due to error**. 
                              | This is the average value read by the counter during the 
                              | collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
errorCum          integer     | **Egress packets dropped cumulative due to error**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
errorMax          integer     | **Egress packets dropped due to error maximum read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
errorMin          integer     | **Egress packets dropped due to error minimum read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
errorPer          integer     | **Egress packets dropped due to error per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
errorRate         float       | **Egress packets dropped due to error rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
intervalStart     time        | **Interval start time**. 
                              | Timestamp of when interval started. 
intervalEnd       time        | **Interval end time**. 
                              | Timestamp of when interval ended. 
================  ==========  =================================================================
