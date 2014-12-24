.. _egrPkts-label:

egrPkts
---------------------------

================  ==========  ==================================================
Name              Type        | Description 
================  ==========  ==================================================
floodAvg          integer     | **Egress flood average packets**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
floodCum          integer     | **Egress flood cumulative packets**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
floodMax          integer     | **Egress flood maximum packets**. 
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
floodMin          integer     | **Egress flood minimum packets**. 
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
floodPer          integer     | **Egress flood packets per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
floodRate         float       | **Egress flood packets rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
multicastAvg      integer     | **Egress multicast packet average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
multicastCum      integer     | **Egress multicast cumulative packets**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
multicastMax      integer     | **Egress multicast packets maximum read**. 
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
multicastMin      integer     | **Egress multicast packets minimum read**. 
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
multicastPer      integer     | **Egress multicast packets per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
multicastRate     float       | **Egress multicast packet rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unicastAvg        integer     | **Egress unicast average packets**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unicastCum        integer     | **Egress unicast packets cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
unicastMax        integer     | **Egress unicast packets maximum read**. 
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
unicastMin        integer     | **Egress unicast packets minimum read**. 
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
unicastPer        integer     | **Egress unicast packets per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
unicastRate       float       | **Egress unicast packet rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
intervalStart     time        | **Interval start time**. 
                              | Timestamp of when interval started. 
intervalEnd       time        | **Interval end time**. 
                              | Timestamp of when interval ended. 
================  ==========  ==================================================
