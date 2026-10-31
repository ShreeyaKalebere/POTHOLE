# Test-set label audit

A box is *unsupported* when none of the independent models detects anything at that place
(IoU >= 0.3, conf >= 0.02). Unsupported small boxes are label errors; unsupported large boxes
are either real damage all models miss or a region-level annotation.

| source | boxes | unsupported | % unsupported | unsupported & area<0.2% |
|---|---|---|---|---|
| BharatPotHole | 422 | 87 | 20.6 | 63 |
| Biankatpas | 88 | 6 | 6.8 | 4 |
| IndianRoads | 221 | 14 | 6.3 | 0 |
| RDD2022_China_Drone | 43 | 3 | 7.0 | 0 |
| RDD2022_China_MotorBike | 119 | 1 | 0.8 | 0 |
| RDD2022_Czech | 59 | 4 | 6.8 | 1 |
| RDD2022_India | 699 | 43 | 6.2 | 7 |
| RDD2022_Japan | 1232 | 73 | 5.9 | 7 |
| RDD2022_Norway | 113 | 49 | 43.4 | 31 |
| RDD2022_United_States | 138 | 8 | 5.8 | 2 |
| RoboflowIIT | 1118 | 98 | 8.8 | 45 |

**All test boxes: 4252. Unsupported by every model: 386 (9.1%). Unsupported and smaller than 0.2% of the image: 160 (3.8%).**

Recall can never exceed the share of GT that contains visible damage, so these boxes bound
the achievable mAP@50 on this test set.