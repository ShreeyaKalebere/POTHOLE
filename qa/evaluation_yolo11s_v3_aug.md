# Final evaluation — yolo11s_v3_aug

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v3_aug\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.670 | 0.559 | 0.610 | 0.616 | 0.308 |
| pothole | 0.665 | 0.514 | 0.580 | 0.580 | 0.290 |
| alligator_crack | 0.675 | 0.605 | 0.638 | 0.651 | 0.327 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 15.5 | 64.7 |
| CPU (i7-13650HX) | 127.4 | 7.9 |

Model size: **19.1 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.232 | 0.206 | 0.131 |
| Biankatpas | 42 | 0.834 | 0.670 | 0.795 |
| IndianRoads | 137 | 0.723 | 0.697 | 0.710 |
| Pothole600 | 75 | 0.992 | 0.987 | 0.992 |
| RDD2022_China_Drone | 69 | 0.718 | 0.541 | 0.633 |
| RDD2022_China_MotorBike | 97 | 0.956 | 0.944 | 0.977 |
| RDD2022_Czech | 65 | 0.239 | 0.430 | 0.283 |
| RDD2022_India | 436 | 0.596 | 0.498 | 0.549 |
| RDD2022_Japan | 842 | 0.695 | 0.637 | 0.692 |
| RDD2022_Norway | 150 | 0.333 | 0.263 | 0.217 |
| RDD2022_United_States | 165 | 0.592 | 0.566 | 0.586 |
| RoboflowIIT | 384 | 0.531 | 0.436 | 0.455 |

Graphs: `runs/yolo11s_v3_aug_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)