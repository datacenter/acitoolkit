.. _ingrTotal-label:

ingrTotal
---------------------------

================  ==========  ==================================================
Name              Type        | Description 
================  ==========  ==================================================
bytesAvg          integer     | **Ingress bytes average** 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
bytesCum          integer     | **Ingress bytes cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
bytesMax          integer     | **Ingress bytes maximum**. 
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
bytesMin          integer     | **Ingress bytes minimum**. 
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
bytesPer          integer     | **Ingress bytes per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets 
                              | to 0 at the beginning of each interval. 
bytesRate         float       | **Ingress byte rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
bytesRateAvg      float       | **Ingress byte rate average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. This value resets 
                              | to 0 at the beginning of each interval and is in 
                              | bytes per second. 
bytesRateMax      float       | **Ingress byte rate maximum**. 
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
bytesRateMin      float       | **Ingress byte rate minimum**. 
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
pktsAvg           integer     | **Ingress packets average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
pktsCum           integer     | **Ingress packets cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
pktsMax           integer     | **Ingress packets maximum value read**. 
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
pktsMin           integer     | **Ingress packets minimum value read**. 
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
pktsRate          float       | **Ingress packet rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
pktsRateAvg       float       | **Ingress packet rate average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. It is measured in packets per second. 
pktsRateMax       float       | **Ingress packet rate maximum**. 
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
pktsRateMin       float       | **Ingress packet rate minimum**. 
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
