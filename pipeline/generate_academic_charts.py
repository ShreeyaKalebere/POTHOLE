import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def generate_charts():
    out_dir = Path("dataset/RoadDamage20K/qa/reports/charts")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Modern styling
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
    
    # -------------------------------------------------------------
    # Chart 1: Class Distribution
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    classes = ['Pothole\n(Class 0)', 'Alligator Crack\n(Class 1)', 'Curated Negatives\n(Normal Road)']
    counts = [6233, 8358, 1598]
    colors = ['#f59e0b', '#06b6d4', '#10b981']
    
    bars = ax.bar(classes, counts, color=colors, width=0.55, edgecolor='black', linewidth=0.8)
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 150, f'{yval:,}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
    ax.set_title('RoadDamage20K: Ground-Truth Annotation Distribution', fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel('Total Verified Annotations / Frames', fontsize=11)
    ax.set_ylim(0, 9500)
    plt.tight_layout()
    fig.savefig(out_dir / "01_class_distribution.png")
    plt.close(fig)
    print("Saved -> 01_class_distribution.png")

    # -------------------------------------------------------------
    # Chart 2: Geographic Source Breakdown
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 7), dpi=300)
    geo_labels = ['Indian Road Conditions\n(Primary Anchor - 4,092)', 'Japan Vehicle Runs\n(Supplementary - 5,038)', 'Czech Road Runs\n(Supplementary - 1,259)']
    geo_sizes = [4092, 5038, 1259]
    geo_colors = ['#4f46e5', '#3b82f6', '#93c5fd']
    explode = (0.05, 0, 0)
    
    wedges, texts, autotexts = ax.pie(
        geo_sizes, explode=explode, labels=geo_labels, colors=geo_colors,
        autopct='%1.1f%%', shadow=False, startangle=140,
        textprops=dict(color="black", fontsize=10)
    )
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
        at.set_fontsize(11)
        
    ax.set_title('Geographic Origin of Unique Road Imagery (N = 10,389)', fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    fig.savefig(out_dir / "02_geographic_sources.png")
    plt.close(fig)
    print("Saved -> 02_geographic_sources.png")

    # -------------------------------------------------------------
    # Chart 3: Zero-Leakage Sequence Partitioning
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 7), dpi=300)
    split_labels = ['Train Split\n(7,270 images)', 'Validation Split\n(1,558 images)', 'Held-Out Test Split\n(1,561 images)']
    split_sizes = [7270, 1558, 1561]
    split_colors = ['#10b981', '#f59e0b', '#ef4444']
    
    wedges, texts, autotexts = ax.pie(
        split_sizes, labels=split_labels, colors=split_colors,
        autopct='%1.1f%%', shadow=False, startangle=90,
        textprops=dict(color="black", fontsize=10)
    )
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
        at.set_fontsize(11)
        
    ax.set_title('Sequence-Clustered Partitioning (Zero Video Leakage)', fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    fig.savefig(out_dir / "03_dataset_splits.png")
    plt.close(fig)
    print("Saved -> 03_dataset_splits.png")

    # -------------------------------------------------------------
    # Chart 4: Hardware Inference Throughput (FPS)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    devices = ['NVIDIA T4 GPU\n(Colab / Server)', 'NVIDIA RTX 3060\n(Workstation)', 'Jetson Orin Nano\n(Vehicle Edge Box)', 'Intel Core i7 CPU\n(Laptop Baseline)']
    fps_values = [162, 145, 42, 33]
    dev_colors = ['#10b981', '#6366f1', '#06b6d4', '#94a3b8']
    
    bars = ax.barh(devices, fps_values, color=dev_colors, height=0.55, edgecolor='black', linewidth=0.8)
    for bar in bars:
        xval = bar.get_width()
        ax.text(xval + 3, bar.get_y() + bar.get_height()/2.0, f'{xval} FPS', ha='left', va='center', fontsize=11, fontweight='bold')
        
    # Add 30 FPS Real-time threshold line
    ax.axvline(30, color='#ef4444', linestyle='--', linewidth=1.5, label='Real-Time Video Threshold (30 FPS)')
    ax.set_title('YOLO11 Nano Inference Speed Across Hardware Platforms', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Frames Per Second (FPS)', fontsize=11)
    ax.set_xlim(0, 190)
    ax.legend(loc='lower right', frameon=True)
    plt.tight_layout()
    fig.savefig(out_dir / "04_inference_throughput_fps.png")
    plt.close(fig)
    print("Saved -> 04_inference_throughput_fps.png")

    # -------------------------------------------------------------
    # Chart 5: Defect Severity Area Heuristic Curves
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    area_pct = np.linspace(0, 15, 300)
    
    # Highlight severity zones
    ax.axvspan(0, 2, color='#10b981', alpha=0.2, label='Pothole: Low (<2%)')
    ax.axvspan(2, 6, color='#f59e0b', alpha=0.2, label='Pothole: Medium (2%-6%)')
    ax.axvspan(6, 15, color='#ef4444', alpha=0.2, label='Pothole: High (≥6%)')
    
    ax.set_title('Image-Based Municipal Damage Severity Decision Boundaries', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Normalized Bounding-Box Area (% of Total Video Frame)', fontsize=11)
    ax.set_ylabel('Severity Category Assigned', fontsize=11)
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(['Low Priority\n(Scheduled)', 'Medium Priority\n(48-Hour Patch)', 'High Hazard\n(Immediate Dispatch)'], fontsize=9)
    ax.set_xlim(0, 15)
    ax.legend(loc='upper right', frameon=True)
    plt.tight_layout()
    fig.savefig(out_dir / "05_severity_heuristics.png")
    plt.close(fig)
    print("Saved -> 05_severity_heuristics.png")

if __name__ == "__main__":
    generate_charts()
