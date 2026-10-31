# Dataset audit

images=17941 label files scanned, bad box records=1, cross-split duplicates=105

## Totals per split

| split | images | boxes | boxes/img | empty img | % empty | pothole | alligator | tiny<0.1% | % tiny | huge>25% | whole frame | dup pairs | class conflicts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test | 2652 | 4327 | 1.63 | 339 | 12.8 | 2726 | 1601 | 453 | 10.5 | 333 | 0 | 1 | 1 |
| train | 12597 | 21183 | 1.68 | 1465 | 11.6 | 13464 | 7719 | 2205 | 10.4 | 1591 | 9 | 4 | 3 |
| val | 2692 | 4776 | 1.77 | 319 | 11.8 | 3112 | 1664 | 464 | 9.7 | 354 | 2 | 4 | 2 |

## Per source (all splits)

| source | split | images | boxes | boxes/img | % empty | tiny<0.1% | % tiny | huge | whole frame | dup | conflicts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BharatPotHole | test | 171 | 422 | 2.47 | 0.0 | 132 | 31.3 | 0 | 0 | 0 | 0 |
| BharatPotHole | train | 900 | 2447 | 2.72 | 0.0 | 669 | 27.3 | 0 | 0 | 0 | 0 |
| BharatPotHole | val | 200 | 855 | 4.28 | 0.0 | 143 | 16.7 | 1 | 0 | 0 | 0 |
| Biankatpas | test | 42 | 88 | 2.1 | 0.0 | 3 | 3.4 | 1 | 0 | 0 | 0 |
| Biankatpas | train | 196 | 456 | 2.33 | 0.0 | 26 | 5.7 | 10 | 0 | 0 | 0 |
| Biankatpas | val | 42 | 91 | 2.17 | 0.0 | 3 | 3.3 | 1 | 0 | 0 | 0 |
| IndianRoads | test | 137 | 221 | 1.61 | 7.3 | 0 | 0.0 | 34 | 0 | 0 | 0 |
| IndianRoads | train | 640 | 1055 | 1.65 | 7.2 | 0 | 0.0 | 143 | 2 | 0 | 0 |
| IndianRoads | val | 137 | 210 | 1.53 | 8.0 | 0 | 0.0 | 29 | 0 | 0 | 0 |
| Pothole600 | test | 75 | 75 | 1.0 | 0.0 | 0 | 0.0 | 0 | 0 | 0 | 0 |
| Pothole600 | train | 434 | 449 | 1.03 | 0.0 | 0 | 0.0 | 45 | 0 | 0 | 0 |
| Pothole600 | val | 80 | 84 | 1.05 | 0.0 | 0 | 0.0 | 23 | 1 | 0 | 0 |
| RDD2022_China_Drone | test | 69 | 43 | 0.62 | 49.3 | 0 | 0.0 | 5 | 0 | 0 | 0 |
| RDD2022_China_Drone | train | 323 | 265 | 0.82 | 29.4 | 0 | 0.0 | 23 | 0 | 0 | 0 |
| RDD2022_China_Drone | val | 69 | 48 | 0.7 | 39.1 | 0 | 0.0 | 4 | 0 | 0 | 0 |
| RDD2022_China_MotorBike | test | 97 | 119 | 1.23 | 16.5 | 7 | 5.9 | 31 | 0 | 0 | 0 |
| RDD2022_China_MotorBike | train | 458 | 557 | 1.22 | 18.1 | 33 | 5.9 | 150 | 0 | 0 | 0 |
| RDD2022_China_MotorBike | val | 98 | 118 | 1.2 | 16.3 | 8 | 6.8 | 31 | 0 | 0 | 0 |
| RDD2022_Czech | test | 65 | 59 | 0.91 | 38.5 | 1 | 1.7 | 0 | 0 | 0 | 0 |
| RDD2022_Czech | train | 308 | 251 | 0.81 | 42.2 | 2 | 0.8 | 0 | 0 | 0 | 0 |
| RDD2022_Czech | val | 66 | 48 | 0.73 | 47.0 | 0 | 0.0 | 0 | 0 | 0 | 0 |
| RDD2022_India | test | 436 | 699 | 1.6 | 13.3 | 2 | 0.3 | 19 | 0 | 1 | 1 |
| RDD2022_India | train | 2039 | 3461 | 1.7 | 11.6 | 17 | 0.5 | 61 | 0 | 3 | 3 |
| RDD2022_India | val | 437 | 739 | 1.69 | 11.2 | 3 | 0.4 | 16 | 0 | 2 | 2 |
| RDD2022_Japan | test | 842 | 1232 | 1.46 | 6.8 | 1 | 0.1 | 142 | 0 | 0 | 0 |
| RDD2022_Japan | train | 3934 | 5927 | 1.51 | 6.4 | 59 | 1.0 | 644 | 2 | 0 | 0 |
| RDD2022_Japan | val | 843 | 1246 | 1.48 | 5.6 | 13 | 1.0 | 140 | 1 | 2 | 0 |
| RDD2022_Norway | test | 150 | 113 | 0.75 | 50.7 | 43 | 38.1 | 0 | 0 | 0 | 0 |
| RDD2022_Norway | train | 705 | 650 | 0.92 | 48.4 | 236 | 36.3 | 0 | 0 | 0 | 0 |
| RDD2022_Norway | val | 151 | 108 | 0.72 | 50.3 | 38 | 35.2 | 0 | 0 | 0 | 0 |
| RDD2022_United_States | test | 165 | 138 | 0.84 | 26.7 | 4 | 2.9 | 6 | 0 | 0 | 0 |
| RDD2022_United_States | train | 773 | 681 | 0.88 | 24.8 | 19 | 2.8 | 40 | 0 | 0 | 0 |
| RDD2022_United_States | val | 165 | 149 | 0.9 | 25.5 | 3 | 2.0 | 10 | 0 | 0 | 0 |
| RoboflowIIT | test | 384 | 1118 | 2.91 | 0.0 | 260 | 23.3 | 95 | 0 | 0 | 0 |
| RoboflowIIT | train | 1795 | 4984 | 2.78 | 0.0 | 1144 | 23.0 | 475 | 5 | 1 | 0 |
| RoboflowIIT | val | 384 | 1080 | 2.81 | 0.0 | 253 | 23.4 | 99 | 0 | 0 | 0 |
| UrbanCivic_no | test | 19 | 0 | 0.0 | 100.0 | 0 | 0.0 | 0 | 0 | 0 | 0 |
| UrbanCivic_no | train | 92 | 0 | 0.0 | 100.0 | 0 | 0.0 | 0 | 0 | 0 | 0 |
| UrbanCivic_no | val | 20 | 0 | 0.0 | 100.0 | 0 | 0.0 | 0 | 0 | 0 | 0 |

## Instance area (fraction of image) per source

| source | split | n | p1 | p5 | median | mean | p95 | p99 | %area<0.1% | %area<0.5% |
|---|---|---|---|---|---|---|---|---|---|---|
| BharatPotHole | test | 422 | 0.0003 | 0.0004 | 0.0017 | 0.0044 | 0.0142 | 0.0423 | 31.3 | 79.1 |
| BharatPotHole | train | 2447 | 0.0001 | 0.0003 | 0.0022 | 0.0060 | 0.0245 | 0.0642 | 27.3 | 74.7 |
| BharatPotHole | val | 855 | 0.0002 | 0.0004 | 0.0026 | 0.0080 | 0.0273 | 0.1232 | 16.7 | 70.6 |
| Biankatpas | test | 88 | 0.0010 | 0.0011 | 0.0033 | 0.0178 | 0.0708 | 0.1816 | 3.4 | 62.5 |
| Biankatpas | train | 456 | 0.0007 | 0.0009 | 0.0045 | 0.0207 | 0.1121 | 0.2685 | 5.7 | 55.9 |
| Biankatpas | val | 91 | 0.0008 | 0.0011 | 0.0066 | 0.0201 | 0.0961 | 0.1714 | 3.3 | 45.1 |
| IndianRoads | test | 221 | 0.0074 | 0.0142 | 0.0751 | 0.1216 | 0.3447 | 0.6327 | 0.0 | 0.0 |
| IndianRoads | train | 1055 | 0.0058 | 0.0131 | 0.0769 | 0.1205 | 0.3800 | 0.4987 | 0.0 | 0.7 |
| IndianRoads | val | 210 | 0.0075 | 0.0124 | 0.0771 | 0.1223 | 0.3701 | 0.5352 | 0.0 | 0.0 |
| Pothole600 | test | 75 | 0.0327 | 0.0346 | 0.0404 | 0.0421 | 0.0494 | 0.0566 | 0.0 | 0.0 |
| Pothole600 | train | 449 | 0.0242 | 0.0315 | 0.0568 | 0.1042 | 0.3580 | 0.5211 | 0.0 | 0.2 |
| Pothole600 | val | 84 | 0.0304 | 0.0365 | 0.0899 | 0.1872 | 0.6666 | 0.6958 | 0.0 | 0.0 |
| RDD2022_China_Drone | test | 43 | 0.0030 | 0.0075 | 0.0473 | 0.0977 | 0.4105 | 0.4820 | 0.0 | 2.3 |
| RDD2022_China_Drone | train | 265 | 0.0043 | 0.0055 | 0.0422 | 0.0824 | 0.3585 | 0.4786 | 0.0 | 2.6 |
| RDD2022_China_Drone | val | 48 | 0.0039 | 0.0047 | 0.0427 | 0.0792 | 0.3448 | 0.4609 | 0.0 | 6.2 |
| RDD2022_China_MotorBike | test | 119 | 0.0004 | 0.0010 | 0.1125 | 0.1767 | 0.5558 | 0.7997 | 5.9 | 20.2 |
| RDD2022_China_MotorBike | train | 557 | 0.0004 | 0.0009 | 0.0747 | 0.1684 | 0.6030 | 0.7938 | 5.9 | 21.9 |
| RDD2022_China_MotorBike | val | 118 | 0.0003 | 0.0008 | 0.0763 | 0.1663 | 0.5245 | 0.8103 | 6.8 | 22.0 |
| RDD2022_Czech | test | 59 | 0.0011 | 0.0014 | 0.0097 | 0.0233 | 0.0924 | 0.1084 | 1.7 | 28.8 |
| RDD2022_Czech | train | 251 | 0.0010 | 0.0016 | 0.0093 | 0.0206 | 0.0687 | 0.1291 | 0.8 | 33.5 |
| RDD2022_Czech | val | 48 | 0.0012 | 0.0016 | 0.0136 | 0.0203 | 0.0671 | 0.1144 | 0.0 | 33.3 |
| RDD2022_India | test | 699 | 0.0012 | 0.0019 | 0.0237 | 0.0600 | 0.2200 | 0.3476 | 0.3 | 21.0 |
| RDD2022_India | train | 3461 | 0.0012 | 0.0019 | 0.0222 | 0.0555 | 0.2061 | 0.2862 | 0.5 | 21.2 |
| RDD2022_India | val | 739 | 0.0013 | 0.0022 | 0.0281 | 0.0603 | 0.2075 | 0.3310 | 0.4 | 18.7 |
| RDD2022_Japan | test | 1232 | 0.0012 | 0.0023 | 0.0529 | 0.0959 | 0.3246 | 0.4255 | 0.1 | 14.5 |
| RDD2022_Japan | train | 5927 | 0.0010 | 0.0021 | 0.0479 | 0.0960 | 0.3364 | 0.5353 | 1.0 | 14.9 |
| RDD2022_Japan | val | 1246 | 0.0010 | 0.0018 | 0.0450 | 0.0959 | 0.3422 | 0.5446 | 1.0 | 14.8 |
| RDD2022_Norway | test | 113 | 0.0001 | 0.0002 | 0.0019 | 0.0096 | 0.0444 | 0.0903 | 38.1 | 66.4 |
| RDD2022_Norway | train | 650 | 0.0001 | 0.0002 | 0.0024 | 0.0096 | 0.0471 | 0.0728 | 36.3 | 62.9 |
| RDD2022_Norway | val | 108 | 0.0001 | 0.0003 | 0.0041 | 0.0117 | 0.0416 | 0.0909 | 35.2 | 55.6 |
| RDD2022_United_States | test | 138 | 0.0006 | 0.0013 | 0.0515 | 0.0775 | 0.2420 | 0.3092 | 2.9 | 16.7 |
| RDD2022_United_States | train | 681 | 0.0008 | 0.0014 | 0.0539 | 0.0797 | 0.2653 | 0.3338 | 2.8 | 13.5 |
| RDD2022_United_States | val | 149 | 0.0008 | 0.0017 | 0.0623 | 0.0891 | 0.2605 | 0.3492 | 2.0 | 12.1 |
| RoboflowIIT | test | 1118 | 0.0002 | 0.0003 | 0.0043 | 0.0624 | 0.4796 | 0.6914 | 23.3 | 52.5 |
| RoboflowIIT | train | 4984 | 0.0002 | 0.0003 | 0.0049 | 0.0680 | 0.4890 | 0.7115 | 23.0 | 50.6 |
| RoboflowIIT | val | 1080 | 0.0002 | 0.0003 | 0.0044 | 0.0656 | 0.5285 | 0.7158 | 23.4 | 52.4 |

## Aspect ratio (w/h) per source

| source | split | p5 | median | p95 |
|---|---|---|---|---|
| BharatPotHole | test | 0.53 | 1.51 | 3.62 |
| BharatPotHole | train | 0.58 | 1.62 | 5.16 |
| BharatPotHole | val | 1.04 | 3.05 | 6.78 |
| Biankatpas | test | 0.41 | 1.14 | 1.95 |
| Biankatpas | train | 0.41 | 1.02 | 1.98 |
| Biankatpas | val | 0.45 | 0.91 | 1.82 |
| IndianRoads | test | 0.37 | 1.07 | 2.83 |
| IndianRoads | train | 0.37 | 0.97 | 2.47 |
| IndianRoads | val | 0.35 | 1.01 | 2.69 |
| Pothole600 | test | 0.74 | 1.01 | 1.36 |
| Pothole600 | train | 0.62 | 0.99 | 1.62 |
| Pothole600 | val | 0.55 | 1.02 | 1.83 |
| RDD2022_China_Drone | test | 0.36 | 0.91 | 4.19 |
| RDD2022_China_Drone | train | 0.33 | 0.99 | 2.91 |
| RDD2022_China_Drone | val | 0.32 | 1.15 | 2.76 |
| RDD2022_China_MotorBike | test | 0.48 | 1.16 | 3.00 |
| RDD2022_China_MotorBike | train | 0.34 | 1.22 | 3.17 |
| RDD2022_China_MotorBike | val | 0.46 | 1.04 | 2.94 |
| RDD2022_Czech | test | 0.78 | 1.63 | 3.05 |
| RDD2022_Czech | train | 0.90 | 1.68 | 3.43 |
| RDD2022_Czech | val | 0.70 | 1.55 | 3.25 |
| RDD2022_India | test | 0.84 | 1.77 | 3.70 |
| RDD2022_India | train | 0.85 | 1.75 | 3.70 |
| RDD2022_India | val | 0.82 | 1.66 | 3.85 |
| RDD2022_Japan | test | 0.62 | 1.42 | 3.13 |
| RDD2022_Japan | train | 0.64 | 1.45 | 3.23 |
| RDD2022_Japan | val | 0.62 | 1.41 | 3.31 |
| RDD2022_Norway | test | 0.34 | 0.74 | 1.83 |
| RDD2022_Norway | train | 0.32 | 0.90 | 2.10 |
| RDD2022_Norway | val | 0.35 | 0.82 | 1.85 |
| RDD2022_United_States | test | 0.60 | 1.13 | 3.01 |
| RDD2022_United_States | train | 0.54 | 1.19 | 2.36 |
| RDD2022_United_States | val | 0.50 | 1.13 | 2.11 |
| RoboflowIIT | test | 0.58 | 1.47 | 3.11 |
| RoboflowIIT | train | 0.61 | 1.50 | 3.16 |
| RoboflowIIT | val | 0.56 | 1.43 | 3.18 |

## Image resolutions (top 15)

| size | count |
|---|---|
| 600x600 | 5743 |
| 640x640 | 4937 |
| 720x720 | 2912 |
| 512x512 | 1114 |
| 1920x1088 | 758 |
| 400x400 | 589 |
| 3643x2041 | 403 |
| 4040x2035 | 378 |
| 1024x640 | 226 |
| 3650x2044 | 225 |
| 1024x1024 | 147 |
| 540x540 | 122 |
| 480x848 | 99 |
| 1024x768 | 57 |
| 1024x630 | 55 |

## Class balance

| source | split | pothole | alligator_crack | % pothole |
|---|---|---|---|---|
| BharatPotHole | test | 422 | 0 | 100.0 |
| BharatPotHole | train | 2447 | 0 | 100.0 |
| BharatPotHole | val | 855 | 0 | 100.0 |
| Biankatpas | test | 88 | 0 | 100.0 |
| Biankatpas | train | 456 | 0 | 100.0 |
| Biankatpas | val | 91 | 0 | 100.0 |
| IndianRoads | test | 221 | 0 | 100.0 |
| IndianRoads | train | 1055 | 0 | 100.0 |
| IndianRoads | val | 210 | 0 | 100.0 |
| Pothole600 | test | 75 | 0 | 100.0 |
| Pothole600 | train | 449 | 0 | 100.0 |
| Pothole600 | val | 84 | 0 | 100.0 |
| RDD2022_China_Drone | test | 10 | 33 | 23.3 |
| RDD2022_China_Drone | train | 58 | 207 | 21.9 |
| RDD2022_China_Drone | val | 4 | 44 | 8.3 |
| RDD2022_China_MotorBike | test | 30 | 89 | 25.2 |
| RDD2022_China_MotorBike | train | 162 | 395 | 29.1 |
| RDD2022_China_MotorBike | val | 29 | 89 | 24.6 |
| RDD2022_Czech | test | 35 | 24 | 59.3 |
| RDD2022_Czech | train | 138 | 113 | 55.0 |
| RDD2022_Czech | val | 24 | 24 | 50.0 |
| RDD2022_India | test | 434 | 265 | 62.1 |
| RDD2022_India | train | 2152 | 1309 | 62.2 |
| RDD2022_India | val | 434 | 305 | 58.7 |
| RDD2022_Japan | test | 316 | 916 | 25.6 |
| RDD2022_Japan | train | 1583 | 4344 | 26.7 |
| RDD2022_Japan | val | 330 | 916 | 26.5 |
| RDD2022_Norway | test | 54 | 59 | 47.8 |
| RDD2022_Norway | train | 303 | 347 | 46.6 |
| RDD2022_Norway | val | 50 | 58 | 46.3 |
| RDD2022_United_States | test | 18 | 120 | 13.0 |
| RDD2022_United_States | train | 100 | 581 | 14.7 |
| RDD2022_United_States | val | 17 | 132 | 11.4 |
| RoboflowIIT | test | 1023 | 95 | 91.5 |
| RoboflowIIT | train | 4561 | 423 | 91.5 |
| RoboflowIIT | val | 984 | 96 | 91.1 |