# Final evaluation — yolo11s_v11_verified

Weights: `F:\POTHOLE_PROJECT\runs\yolo11s_v11_verified\weights\best.pt`  
Test set: 2,652 images of the old test set

**Not a clean test for this model. Do not report these accuracy numbers as an improvement over v1-v8.**
v11 uses a separately split dataset: 1,328 of these images are byte-identical to images in its training set,
and 269 more to images in its validation set. Only 1,055 have no identical copy in its train or val sets.
Clean v11 result: `qa/evaluation_yolo11s_v11_verified_verified_test.md`.

## Accuracy (test set)

| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| All | 0.728 | 0.625 | 0.672 | 0.696 | 0.368 |
| pothole | 0.744 | 0.587 | 0.657 | 0.674 | 0.361 |
| alligator_crack | 0.711 | 0.663 | 0.686 | 0.718 | 0.375 |

## Speed

| Device | ms / image | FPS |
|---|---|---|
| GPU (RTX 4060 Laptop) | 8.8 | 114.1 |
| CPU (i7-13650HX) | 126.6 | 7.9 |

Model size: **56.9 MB**, parameters: **9.43 M**

## mAP@50 by data source (test images)

| Source | Test images | Precision | Recall | mAP@50 |
|---|---|---|---|---|
| BharatPotHole | 171 | 0.399 | 0.344 | 0.300 |
| Biankatpas | 42 | 0.859 | 0.795 | 0.879 |
| IndianRoads | 137 | 0.778 | 0.665 | 0.726 |
| Pothole600 | 75 | 1.000 | 1.000 | 0.995 |
| RDD2022_China_Drone | 69 | 0.500 | 0.715 | 0.621 |
| RDD2022_China_MotorBike | 97 | 0.952 | 0.893 | 0.948 |
| RDD2022_Czech | 65 | 0.435 | 0.421 | 0.397 |
| RDD2022_India | 436 | 0.669 | 0.588 | 0.621 |
| RDD2022_Japan | 842 | 0.735 | 0.720 | 0.780 |
| RDD2022_Norway | 150 | 0.589 | 0.318 | 0.323 |
| RDD2022_United_States | 165 | 0.729 | 0.725 | 0.736 |
| RoboflowIIT | 384 | 0.484 | 0.556 | 0.504 |

Graphs: `runs/yolo11s_v11_verified_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)