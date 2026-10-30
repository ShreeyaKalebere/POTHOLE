# Dataset Health Report

Final images: **17941**

| Source | Images | Train | Val | Test | Pothole boxes | Alligator boxes | Background imgs |
|---|---|---|---|---|---|---|---|
| BharatPotHole | 1271 | 900 | 200 | 171 | 3724 | 0 | 0 |
| Biankatpas | 280 | 196 | 42 | 42 | 635 | 0 | 0 |
| IndianRoads | 914 | 640 | 137 | 137 | 1486 | 0 | 67 |
| Pothole600 | 589 | 434 | 80 | 75 | 608 | 0 | 0 |
| RDD2022_China_Drone | 461 | 323 | 69 | 69 | 72 | 284 | 156 |
| RDD2022_China_MotorBike | 653 | 458 | 98 | 97 | 221 | 573 | 115 |
| RDD2022_Czech | 439 | 308 | 66 | 65 | 197 | 161 | 186 |
| RDD2022_India | 2912 | 2039 | 437 | 436 | 3020 | 1879 | 343 |
| RDD2022_Japan | 5619 | 3934 | 843 | 842 | 2229 | 6176 | 354 |
| RDD2022_Norway | 1006 | 705 | 151 | 150 | 407 | 464 | 493 |
| RDD2022_United_States | 1103 | 773 | 165 | 165 | 135 | 833 | 278 |
| RoboflowIIT | 2563 | 1795 | 384 | 384 | 6568 | 614 | 0 |
| UrbanCivic_no | 131 | 92 | 20 | 19 | 0 | 0 | 131 |
| **TOTAL** | **17941** | 12597 | 2692 | 2652 | **19302** | **10984** | 2123 |

## Box sizes (area as % of image)

| Class | Size | Count |
|---|---|---|
| alligator_crack | large(>10%) | 4538 |
| alligator_crack | medium(1-10%) | 5556 |
| alligator_crack | small(<1%) | 890 |
| pothole | large(>10%) | 1962 |
| pothole | medium(1-10%) | 5147 |
| pothole | small(<1%) | 12193 |

## Removed / fixed

| Reason | Count |
|---|---|
| negative images beyond 10% cap (not needed) | 28670 |
| RDD2022: test folder has zero labels (9035 imgs) - not used | 9035 |
| image: no usable boxes and not a trusted negative | 4651 |
| image: near-duplicate of another image | 3685 |
| Biankatpas: crack-only image (generic cracks, not alligator) - skipped | 1127 |
| box: too small / outside image | 765 |
| IndianRoads: screenshot of another model's output (FPS/labels burned in) | 539 |
| IndianRoads: '- Copy' duplicate file | 50 |
| Biankatpas: missing RAW or POTHOLE mask | 28 |

## Not used for training (no box labels)

- SPDataset (618 images) - no annotations -> use for demo / pseudo-labeling later
- Urban Civic/yes (1004 images) - only 'has pothole' tag, no boxes -> pseudo-label later