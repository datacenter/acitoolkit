.. _egrTotal-label:

egrTotal
---------------------------

================  ==========  ==================================================
Name              Type        | Description 
================  ==========  ==================================================
bytesAvg          integer     | **Egress bytes average** 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
bytesCum          integer     | **Egress bytes cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
bytesMax          integer     | **Egress bytes maximum**. 
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
bytesMin          integer     | **Egress bytes minimum**. 
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
bytesPer          integer     | **Egress bytes per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
bytesRate         float       | **Egress byte rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
bytesRateAvg      float       | **Egress byte rate average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. This value resets 
                              | to 0 at the beginning of each interval and is in 
                              | bytes per second. 
bytesRateMax      float       | **Egress byte rate maximum**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is 
                              | smaller than 4, the value remains at 4. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. It is in bytes per second. 
bytesRateMin      float       | **Egress byte rate minimum**. 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | smaller than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is 
                              | larger than 2, the value remains at 2. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. It is measured in bytes per second. 
pktsAvg           integer     | **Egress packets average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
pktsCum           integer     | **Egress packets cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
pktsMax           integer     | **Egress packets maximum value read**. 
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
pktsMin           integer     | **Egress packets minimum value read**. 
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
pktsPer           integer     | **Egres packets per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
pktsRate          float       | **Egress packet rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
pktsRateAvg       float       | **Egress packet rate average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. It is measured in packets per second. 
pktsRateMax       float       | **Egress packet rate maximum**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | larger than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is 
                              | smaller than 4, the value remains at 4. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. It is measured in packets per second. 
pktsRateMin       float       | **Egress packet rate minimum**. 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is 
                              | only overwritten if the most current value is 
                              | smaller than the previous value. For example, if 
                              | the value of the first reading is 3 and the value 
                              | of the second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is 
                              | larger than 2, the value remains at 2. Note that 
                              | this value resets to 0 at the beginning of each 
                              | interval. It is measured in packets per second. 
intervalStart     time        | **Interval start time**. 
                              | Timestamp of when interval started. 
intervalEnd       time        | **Interval end time**. 
                              | Timestamp of when interval ended. 
================  ==========  ==================================================
