# Final evaluation — yolo11s_v5_kolpseudo

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v5_kolpseudo\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.667 | 0.575 | 0.618 | 0.618 | 0.307 |
| pothole | 0.664 | 0.523 | 0.585 | 0.582 | 0.290 |
| alligator_crack | 0.671 | 0.627 | 0.648 | 0.653 | 0.325 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 8.3 | 120.6 |
| CPU (i7-13650HX) | 100.7 | 9.9 |

Model size: **19.1 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.275 | 0.230 | 0.163 |
| Biankatpas | 42 | 0.782 | 0.716 | 0.777 |
| IndianRoads | 137 | 0.743 | 0.670 | 0.705 |
| Pothole600 | 75 | 0.999 | 0.987 | 0.995 |
| RDD2022_China_Drone | 69 | 0.665 | 0.614 | 0.612 |
| RDD2022_China_MotorBike | 97 | 0.969 | 0.931 | 0.977 |
| RDD2022_Czech | 65 | 0.389 | 0.415 | 0.323 |
| RDD2022_India | 436 | 0.592 | 0.542 | 0.556 |
| RDD2022_Japan | 842 | 0.693 | 0.659 | 0.689 |
| RDD2022_Norway | 150 | 0.405 | 0.249 | 0.205 |
| RDD2022_United_States | 165 | 0.695 | 0.567 | 0.606 |
| RoboflowIIT | 384 | 0.492 | 0.450 | 0.441 |

Graphs: `runs/yolo11s_v5_kolpseudo_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)