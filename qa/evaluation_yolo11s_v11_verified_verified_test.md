# yolo11s_v11_verified: verified test set

Weights: `runs/yolo11s_v11_verified/weights/best.pt`, 640 px.

| Set | Images | Precision | Recall | mAP@50 | mAP@50-95 |
|---|---:|---:|---:|---:|---:|
| **All test** | 3078 | 0.690 | 0.572 | 0.631 | 0.330 |
| pothole | | 0.702 | 0.571 | 0.630 | 0.321 |
| alligator_crack | | 0.679 | 0.573 | 0.632 | 0.338 |

## Per source

| Source | Images | Precision | Recall | mAP@50 | mAP@50-95 |
|---|---:|---:|---:|---:|---:|
| RDD2022Dataset | 1685 | 0.668 | 0.601 | 0.657 | 0.335 |
| RoboflowIIT | 376 | 0.531 | 0.428 | 0.448 | 0.217 |
| BharatPotHole | 217 | 0.385 | 0.657 | 0.227 | 0.080 |
| IndianRoadsDataset | 180 | 0.334 | 0.297 | 0.328 | 0.162 |
| UrbanCivic | 175 | 0.525 | 0.544 | 0.559 | 0.343 |
| kolhapur_test | 152 | 0.631 | 0.193 | 0.215 | 0.112 |
| Pothole600 | 100 | 0.931 | 0.923 | 0.962 | 0.669 |
| fix_labels_val | 72 | 0.449 | 0.450 | 0.430 | 0.214 |
| SPDataset | 69 | 0.454 | 0.501 | 0.471 | 0.208 |
| BiankatpasDataset | 52 | 0.647 | 0.675 | 0.649 | 0.321 |

## Recall by box size at 640 px (conf 0.25, IoU 0.5)

| Class | Size | Boxes | Found | Recall |
|---|---|---:|---:|---:|
| pothole | under 16 px | 334 | 85 | 0.254 |
| pothole | 16-32 px | 737 | 371 | 0.503 |
| pothole | 32-96 px | 1591 | 841 | 0.529 |
| pothole | over 96 px | 1185 | 865 | 0.730 |
| alligator_crack | under 16 px | 7 | 0 | 0.000 |
| alligator_crack | 16-32 px | 22 | 0 | 0.000 |
| alligator_crack | 32-96 px | 361 | 98 | 0.271 |
| alligator_crack | over 96 px | 1656 | 1082 | 0.653 |
