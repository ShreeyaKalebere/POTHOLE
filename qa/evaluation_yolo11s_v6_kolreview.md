# Final evaluation — yolo11s_v6_kolreview

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v6_kolreview\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.690 | 0.567 | 0.623 | 0.623 | 0.312 |
| pothole | 0.682 | 0.522 | 0.591 | 0.586 | 0.294 |
| alligator_crack | 0.698 | 0.613 | 0.653 | 0.659 | 0.329 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 16.1 | 62.0 |
| CPU (i7-13650HX) | 121.6 | 8.2 |

Model size: **19.1 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.249 | 0.280 | 0.165 |
| Biankatpas | 42 | 0.828 | 0.670 | 0.789 |
| IndianRoads | 137 | 0.765 | 0.674 | 0.723 |
| Pothole600 | 75 | 0.999 | 0.987 | 0.995 |
| RDD2022_China_Drone | 69 | 0.765 | 0.627 | 0.639 |
| RDD2022_China_MotorBike | 97 | 0.964 | 0.937 | 0.972 |
| RDD2022_Czech | 65 | 0.345 | 0.394 | 0.293 |
| RDD2022_India | 436 | 0.590 | 0.547 | 0.566 |
| RDD2022_Japan | 842 | 0.705 | 0.625 | 0.686 |
| RDD2022_Norway | 150 | 0.439 | 0.254 | 0.217 |
| RDD2022_United_States | 165 | 0.745 | 0.551 | 0.630 |
| RoboflowIIT | 384 | 0.516 | 0.433 | 0.424 |

Graphs: `runs/yolo11s_v6_kolreview_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)