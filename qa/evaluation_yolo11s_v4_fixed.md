# Final evaluation — yolo11s_v4_fixed

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v4_fixed\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.682 | 0.572 | 0.623 | 0.626 | 0.313 |
| pothole | 0.686 | 0.527 | 0.596 | 0.592 | 0.295 |
| alligator_crack | 0.678 | 0.618 | 0.647 | 0.661 | 0.330 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 10.9 | 91.6 |
| CPU (i7-13650HX) | 119.1 | 8.4 |

Model size: **19.2 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.281 | 0.280 | 0.176 |
| Biankatpas | 42 | 0.832 | 0.727 | 0.825 |
| IndianRoads | 137 | 0.784 | 0.658 | 0.724 |
| Pothole600 | 75 | 0.999 | 0.987 | 0.995 |
| RDD2022_China_Drone | 69 | 0.553 | 0.687 | 0.622 |
| RDD2022_China_MotorBike | 97 | 0.934 | 0.944 | 0.966 |
| RDD2022_Czech | 65 | 0.413 | 0.365 | 0.358 |
| RDD2022_India | 436 | 0.627 | 0.533 | 0.575 |
| RDD2022_Japan | 842 | 0.722 | 0.615 | 0.686 |
| RDD2022_Norway | 150 | 0.428 | 0.254 | 0.233 |
| RDD2022_United_States | 165 | 0.765 | 0.554 | 0.623 |
| RoboflowIIT | 384 | 0.530 | 0.409 | 0.433 |

Graphs: `runs/yolo11s_v4_fixed_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)