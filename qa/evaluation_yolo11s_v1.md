# Final evaluation — yolo11s_v1

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v1\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.677 | 0.588 | 0.630 | 0.639 | 0.325 |
| pothole | 0.675 | 0.529 | 0.593 | 0.598 | 0.304 |
| alligator_crack | 0.680 | 0.647 | 0.663 | 0.681 | 0.346 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 8.9 | 111.9 |
| CPU (i7-13650HX) | 104.5 | 9.6 |

Model size: **19.2 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.280 | 0.273 | 0.180 |
| Biankatpas | 42 | 0.787 | 0.739 | 0.797 |
| IndianRoads | 137 | 0.728 | 0.713 | 0.718 |
| Pothole600 | 75 | 0.987 | 0.999 | 0.995 |
| RDD2022_China_Drone | 69 | 0.615 | 0.632 | 0.603 |
| RDD2022_China_MotorBike | 97 | 0.975 | 0.927 | 0.975 |
| RDD2022_Czech | 65 | 0.391 | 0.492 | 0.378 |
| RDD2022_India | 436 | 0.597 | 0.542 | 0.578 |
| RDD2022_Japan | 842 | 0.700 | 0.662 | 0.711 |
| RDD2022_Norway | 150 | 0.395 | 0.254 | 0.240 |
| RDD2022_United_States | 165 | 0.699 | 0.600 | 0.651 |
| RoboflowIIT | 384 | 0.519 | 0.466 | 0.468 |

Graphs: `runs/yolo11s_v1_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)