.. _ingrUnkPkts-label:

ingrUnkPkts
---------------------------

================  ==========  ====================================================
Name              Type        | Description 
================  ==========  ====================================================
unclassifiedAvg   integer     | **Ingress unclassified packets average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unclassifiedCum   integer     | **Ingress unclassified packets cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
unclassifiedMax   integer     | **Ingress unclassified packets max value read**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is only 
                              | overwritten if the most current value is larger 
                              | than the previous value. For example, if the value 
                              | of the first reading is 3 and the value of the 
                              | second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is smaller 
                              | than 4, the value remains at 4. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unclassifiedMin   integer     | **Ingress unclassified packets min value read**. 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is only 
                              | overwritten if the most current value is smaller 
                              | than the previous value. For example, if the value 
                              | of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is larger 
                              | than 2, the value remains at 2. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unclassifiedPer   integer     | **Ingress unclassified packets per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets to 
                              | 0 at the beginning of each interval. 
unclassifiedRate  float       | **Ingress packet rate**. 
                              | This is the rate of the counter during the 
                              | collection interval. The rate is calculated by 
                              | dividing the periodic value by the length of the 
                              | collection interval in seconds. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unicastAvg        integer     | **Ingress unknown unicast packets average**. 
                              | This is the average value read by the counter 
                              | during the collection interval. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unicastCum        integer     | **Ingress unknown unicast packets cumulative**. 
                              | The total sum of the values read. Note that this 
                              | value continues through each interval without 
                              | resetting to zero. 
unicastMax        integer     | **Ingress unknown unicast packets max value read**. 
                              | This is the largest value read by the counter 
                              | during the collection interval. This value is only 
                              | overwritten if the most current value is larger 
                              | than the previous value. For example, if the value 
                              | of the first reading is 3 and the value of the 
                              | second reading is 4, the previous value is 
                              | overwritten with 4. If the third reading is smaller 
                              | than 4, the value remains at 4. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unicastMin        integer     | **Ingress unknown unicast packets min value read**. 
                              | This is the smallest value read by the counter 
                              | during the collection interval. This value is only 
                              | overwritten if the most current value is smaller 
                              | than the previous value. For example, if the value 
                              | of the first reading is 3 and the value of the 
                              | second reading is 2, the previous value is 
                              | overwritten with 2. If the third reading is larger 
                              | than 2, the value remains at 2. Note that this 
                              | value resets to 0 at the beginning of each 
                              | interval. 
unicastPer        integer     | **Ingress unknown unicast packets per interval**. 
                              | The total sum of the values read during the 
                              | collection interval. Note that this value resets to 
                              | 0 at the beginning of each interval. 
unicastRate       float       | **Ingress packet rate**. 
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
================  ==========  ====================================================
