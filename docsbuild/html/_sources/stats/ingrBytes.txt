.. _ingrBytes-label:

ingrBytes
---------------------------

================  ==========  ==================================================
Name              Type        | Description 
================  ==========  ==================================================
floodavg          integer     | **Ingress flood bytes average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
floodCum          integer     | **Ingress flood bytes cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
floodMax          integer     | **Ingress flood bytes maximum**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is 
                              | smaller than 4, the value remains at 4. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. 
floodMin          integer     | **Ingress flood bytes minimum**. 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | smaller than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is 
                              | larger than 2, the value remains at 2. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. 
floodPer          integer     | **Ingress flood bytes total in period** 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
multicastAvg      integer     | **Ingress multicast bytes average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
multicastCum      integer     | **Ingress multicast bytes cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
multicastMax      integer     | **Ingress multicast bytes maximum**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is 
                              | smaller than 4, the value remains at 4. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. 
multicastMin      integer     | **Ingress multicast bytes minimum**. 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | smaller than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is 
                              | larger than 2, the value remains at 2. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. 
multicastPer      integer     | **Ingress multicast bytes per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
floodRate         float       | **Ingress flood byte rate** 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
multicastRate     float       | **Ingress multicast byte rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
multicastRateAvg  float       | **Ingress multicast byte rate average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. This value is in bytes per second. 
multicastRateMax  float       | **Ingress multicast byte rate maximum**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is 
                              | smaller than 4, the value remains at 4. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. This value is in bytes per second. 
multicastRateMin  float       | **Ingress multicast byte rate minimum** 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | smaller than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is 
                              | larger than 2, the value remains at 2. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. This value is in bytes per second. 
intervalStart     time        | **Interval start time**. 
                              | Timestamp of when interval started. 
intervalEnd       time        | **Interval end time**. 
                              | Timestamp of when interval ended. 
================  ==========  ==================================================
