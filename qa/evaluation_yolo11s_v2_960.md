# Final evaluation — yolo11s_v2_960

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v2_960\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.673 | 0.572 | 0.618 | 0.608 | 0.296 |
| pothole | 0.672 | 0.526 | 0.590 | 0.584 | 0.283 |
| alligator_crack | 0.674 | 0.617 | 0.644 | 0.633 | 0.308 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 13.7 | 72.7 |
| CPU (i7-13650HX) | 195.9 | 5.1 |

Model size: **19.2 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.257 | 0.275 | 0.163 |
| Biankatpas | 42 | 0.704 | 0.795 | 0.784 |
| IndianRoads | 137 | 0.762 | 0.739 | 0.739 |
| Pothole600 | 75 | 0.999 | 0.987 | 0.994 |
| RDD2022_China_Drone | 69 | 0.654 | 0.512 | 0.569 |
| RDD2022_China_MotorBike | 97 | 0.927 | 0.956 | 0.957 |
| RDD2022_Czech | 65 | 0.283 | 0.390 | 0.243 |
| RDD2022_India | 436 | 0.615 | 0.526 | 0.553 |
| RDD2022_Japan | 842 | 0.686 | 0.668 | 0.687 |
| RDD2022_Norway | 150 | 0.328 | 0.299 | 0.238 |
| RDD2022_United_States | 165 | 0.744 | 0.535 | 0.610 |
| RoboflowIIT | 384 | 0.564 | 0.466 | 0.463 |

Graphs: `runs/yolo11s_v2_960_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)