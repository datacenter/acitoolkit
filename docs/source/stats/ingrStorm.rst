.. _ingrStorm-label:

ingrStorm
---------------------------

================  ==========  ==================================================
Name              Type        | Description 
================  ==========  ==================================================
dropBytesAvg      integer     | **Ingress ave bytes dropped due to storm control**.
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
dropBytesCum      integer     | **Ingress cum bytes dropped due to storm control** 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
dropBytesMax      integer     | **Ingress max bytes dropped due to storm control**. 
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
dropBytesMin      integer     | **Ingress min bytes dropped due to storm control** 
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
dropBytesPer      integer     | **Ingress bytes dropped per interval due to storm** 
                              | **control** 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
dropBytesRate     integer     | **Ingress byte drop rate due to storm control** 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
dropBytesRateAvg  integer     | **Ingress byte drop rate average due to storm** 
                              | **control** 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. This value is in bytes per second. 
dropBytesRateMax  integer     | **Ingress byte drop rate max due to storm control** 
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
dropBytesRateMin  integer     | **Ingress byte drop rate min due to storm control** 
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
