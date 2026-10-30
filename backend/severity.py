"""Module 3 - Image-based severity estimation (Low / Medium / High).

Idea: a bigger damaged area = more severe. But in a road photo, damage far away
(near the top of the frame) looks smaller than it really is, so we correct for
perspective using how high the box sits in the image.

    score = sqrt(box_area / image_area) * perspective_factor

Thresholds are set PER CLASS from the score distribution of the 21,000 training
boxes, so that roughly 50% of damage is Low, 30% Medium and 20% High.
(Alligator-crack boxes are naturally much bigger than pothole boxes, so one
shared threshold would mark almost every crack High.)

  class            50th pct   80th pct   ->  Low < t1 <= Medium < t2 <= High
  pothole          0.098      0.272          t1 = 0.10, t2 = 0.30
  alligator_crack  0.247      0.379          t1 = 0.25, t2 = 0.40
"""
import math

THRESHOLDS = {"pothole": (0.10, 0.30), "alligator_crack": (0.25, 0.40)}
SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3}


def severity_score(xc, yc, w, h, damage_type=None):
    """xc, yc, w, h normalised 0..1 (YOLO format)."""
    area = max(w * h, 1e-6)
    bottom = min(1.0, yc + h / 2)
    perspective = 1.0 + 1.2 * (1.0 - bottom)          # farther up the frame -> boost
    return round(math.sqrt(area) * perspective, 4)


def severity_label(score, damage_type="pothole"):
    t1, t2 = THRESHOLDS.get(damage_type, THRESHOLDS["pothole"])
    if score < t1:
        return "Low"
    if score < t2:
        return "Medium"
    return "High"
