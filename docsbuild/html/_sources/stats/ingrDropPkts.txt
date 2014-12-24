.. _ingrDropPkts-label:

ingrDropPkts
---------------------------

================  ==========  =================================================================
Name              Type        | Description 
================  ==========  =================================================================
bufferAvg         integer     | **Ingress packets dropped due to buffer full**. 
                              | This is the average value read by the counter during the 
                              | collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
bufferCum         integer     | **Ingress packets dropped cumulative due to buffer full**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
bufferMax         integer     | **Ingress packets dropped due to buffer full max read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
bufferMin         integer     | **Ingress packets dropped due to buffer full min read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
bufferPer         integer     | **Ingress packets dropped due to buffer full per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
bufferRate        float       | **Ingress packets dropped due to buffer full rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
errorAvg          integer     | **Ingress packets dropped due to error**. 
                              | This is the average value read by the counter during the 
                              | collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
errorCum          integer     | **Ingress packets dropped cumulative due to error**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
errorMax          integer     | **Ingress packets dropped due to error max read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
errorMin          integer     | **Ingress packets dropped due to error min read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
errorPer          integer     | **Ingress packets dropped due to error per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
errorRate         float       | **Ingress packets dropped due to error rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
forwardingAvg     integer     | **Ingress packets dropped due to forwarding**. 
                              | This is the average value read by the counter during the 
                              | collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
forwardingCum     integer     | **Ingress packets dropped cumulative due to forwarding**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
forwardingMax     integer     | **Ingress packets dropped due to forwarding max read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
forwardingMin     integer     | **Ingress packets dropped due to forwarding min read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
forwardingPer     integer     | **Ingress packets dropped due to forwarding per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
forwardingRate    float       | **Ingress packets dropped due to forwarding rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
lbAvg             integer     | **Ingress packets dropped due to load balancing**. 
                              | This is the average value read by the counter during the 
                              | collection interval. Note that this value resets to 0 at the 
                              | beginning of each interval. 
lbCum             integer     | **Ingress packets dropped cumulative due to load balancing**. 
                              | The total sum of the values read. Note that this value continues 
                              | through each interval without resetting to zero. 
lbMax             integer     | **Ingress packets dropped due to load balancing max read**. 
                              | This is the largest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value of the second 
                              | reading is 4, the previous value is overwritten with 4. If the 
                              | third reading is smaller than 4, the value remains at 4. Note 
                              | that this value resets to 0 at the beginning of each interval. 
lbMin             integer     | **Ingress packets dropped due to load balancing min read**. 
                              | This is the smallest value read by the counter during the 
                              | collection interval. This value is only overwritten if the most 
                              | current value is smaller than the previous value. For example, 
                              | if the value of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is overwritten with 2. 
                              | If the third reading is larger than 2, the value remains at 2. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
lbPer             integer     | **Ingress packets dropped due to load balancing per interval**. 
                              | The total sum of the values read during the collection interval. 
                              | Note that this value resets to 0 at the beginning of each 
                              | interval. 
lbRate            float       | **Ingress packets dropped due to load balancing rate**. 
                              | This is the rate of the counter during the collection interval. 
                              | The rate is calculated by dividing the periodic value by the 
                              | length of the collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each interval. 
intervalStart     time        | **Interval start time**. 
                              | Timestamp of when interval started. 
intervalEnd       time        | **Interval end time**. 
                              | Timestamp of when interval ended. 
================  ==========  =================================================================
