# Final evaluation — yolo11s_v8_clean

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v8_clean\weights\best.pt`  
Test set: 2,652 images never seen during training

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.659 | 0.557 | 0.604 | 0.600 | 0.303 |
| pothole | 0.662 | 0.477 | 0.554 | 0.544 | 0.277 |
| alligator_crack | 0.655 | 0.637 | 0.646 | 0.657 | 0.328 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 8.5 | 117.3 |
| CPU (i7-13650HX) | 106.5 | 9.4 |

Model size: **19.1 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.305 | 0.225 | 0.164 |
| Biankatpas | 42 | 0.752 | 0.724 | 0.782 |
| IndianRoads | 137 | 0.754 | 0.679 | 0.728 |
| Pothole600 | 75 | 0.999 | 0.987 | 0.994 |
| RDD2022_China_Drone | 69 | 0.622 | 0.617 | 0.605 |
| RDD2022_China_MotorBike | 97 | 0.951 | 0.900 | 0.966 |
| RDD2022_Czech | 65 | 0.270 | 0.386 | 0.272 |
| RDD2022_India | 436 | 0.590 | 0.544 | 0.544 |
| RDD2022_Japan | 842 | 0.695 | 0.623 | 0.674 |
| RDD2022_Norway | 150 | 0.382 | 0.210 | 0.187 |
| RDD2022_United_States | 165 | 0.710 | 0.507 | 0.652 |
| RoboflowIIT | 384 | 0.534 | 0.414 | 0.405 |

Graphs: `runs/yolo11s_v8_clean_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)