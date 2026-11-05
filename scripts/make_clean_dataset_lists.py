import os
import csv
from pathlib import Path

ROOT = Path("F:/POTHOLE_PROJECT")
MANIFEST = ROOT / "dataset_verified" / "manifest.csv"

TOXIC_DATASETS = {"BharatPotHole", "IndianRoadsDataset", "UrbanCivic"}
TOXIC_PREFIXES = ("Norway_", "Czech_")
CORRUPT_FILES = {
    "Japan_010815", "pa3558_jpg", "pa3357_jpg", "pa2193_jpg", "Japan_001119",
    "RDD2022_Japan__009526", "251BDF0052_00980", "0084.png", "China_MotorBike_000816",
    "India_004370", "Japan_006047", "Japan_012704", "United_States_002496",
    "Japan_011938", "pa047_jpg", "Img (309)", "Japan_003684", "India_007446", "Japan_007676", "India_007299",
    "Japan_002654", "Japan_012789", "img-299_jpg.rf.56b911b1621849c1f8ff7e4b923980f8",
    "shubh_IMG_20261027_142242209", "RoboflowIIT__002852", "Japan_004650", "Japan_009725",
    "United_States_003007", "India_004839", "Japan_001762", "Japan_002652", "Japan_003041",
    "Japan_004542", "Japan_005955", "pa1530_jpg", "pa3167_jpg", "pa3079_jpg", "pa592_jpg",
    "Shree_20261027_142554_0052s", "Shree_20261027_143831_0001s", "Vru_20261027_140610_0001s",
    "shubh_VID_20261027_140610241_0167s", "shubh_VID_20261027_140610241_0682s",
    # Additional C++ / NTFS decode hang images identified in deep scans:
    "941509_RS_290_290RS070691_00450_RAW", "0007.png", "China_Drone_002030", "India_000285",
    "India_001165", "India_005886", "India_006529", "India_007981", "Japan_001228",
    "Japan_001763", "Japan_002979", "Japan_003183", "Japan_003770", "Japan_007506",
    "Japan_007916", "Japan_008630", "Japan_009207", "Japan_010479", "Japan_010556",
    "Japan_010933", "Japan_011081", "United_States_000900", "United_States_002497",
    "United_States_002520", "India_002740", "India_004435", "India_005572",
    "Japan_001051", "Japan_007405", "United_States_005934",
    "img-219_jpg.rf.fa14a89643bc395d5d76a1e81083e306",
    "img-290_jpg.rf.b81da15755292eabc1b03646aaa53974",
    "img-75_jpg.rf.f42cceeffd1135d4317a718349b7fecd",
    "pa1299_jpg.rf.b81d13fa0c18122cb69e8d123b918d2d",
    "pa1669_jpg.rf.7411fc02be0aab3e658820f4a3b317da",
    "pa241_jpg.rf.0bbe2c243329c2327aacd5d3488712dd",
    "pa2512_jpg.rf.0d2ec831f927fbda2907580d4ba3b738",
    "pa609_jpg.rf.5af302b609ace11a2129f3ff3889e34b",
    "SPDataset_001/480.jpg", "SPDataset_001\\480.jpg",
    # Val hung files:
    "China_MotorBike_001680", "India_009245", "Japan_001093", "Japan_003844",
    "Japan_004249", "Japan_006347", "Japan_007229", "Japan_007882", "Japan_008439",
    "Japan_010287", "Japan_011356", "Japan_012416", "United_States_000578",
    "United_States_000963", "India_008303",
    "pa1727_jpg.rf.02b6eb9b3be6653f28c16ee8229760e2",
    "pa3262_jpg.rf.59a7729e6081d95e72c4b583755d9cbd",
    # Test hung files:
    "RoboflowIIT__003799", "0058.png", "0008.png", "0024.png",
    "India_004832", "India_006077", "India_009603", "Japan_003491", "Japan_006954",
    "Japan_010472", "Japan_013017", "United_States_003708", "India_004708",
    "India_009291", "img-430_jpg.rf.52e8814166066b2bb6df6460e21367b0",
    "pa2241_jpg.rf.f8831fd8359f6666fe08262fc4cf6a70",
    "pa3443_jpg.rf.f7e7e14f2ba58d99d4f6802b06ef8be6"
}

def is_excluded(dataset_name, file_name):
    full_rel = f"{dataset_name}/{file_name}".replace("\\", "/")
    for td in TOXIC_DATASETS:
        if td in dataset_name or td in file_name:
            return True
    for tp in TOXIC_PREFIXES:
        if file_name.startswith(tp):
            return True
    for cf in CORRUPT_FILES:
        cf_norm = cf.replace("\\", "/")
        if cf_norm in file_name or cf_norm in full_rel:
            return True
    return False

def main():
    with open(MANIFEST, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        
    print(f"Total manifest rows: {len(rows)}")
    
    train_paths = []
    kol_train_paths = []
    val_paths = []
    test_paths = []
    kol_test_paths = []
    
    excluded_count = 0
    kol_train_count = 0
    
    for r in rows:
        split, ds, fn = r["split"], r["dataset"], r["file"]
        if is_excluded(ds, fn):
            excluded_count += 1
            continue
            
        p = os.path.normpath(str(ROOT / "dataset_verified" / "images" / split / ds / fn))
        if not os.path.exists(p):
            continue
            
        # Check label file exists
        lp = p.replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}").rsplit(".", 1)[0] + ".txt"
        if not os.path.exists(lp):
            continue
            
        if split == "train":
            train_paths.append(p)
            if "kolhapur" in ds:
                kol_train_count += 1
                kol_train_paths.append(p)
        elif split == "val":
            val_paths.append(p)
        elif split == "test":
            test_paths.append(p)
            if "kolhapur" in ds:
                kol_test_paths.append(p)

    # 4x oversampling of Kolhapur: append in separate passes separated by full dataset
    for _ in range(3):
        train_paths.extend(kol_train_paths)

    out_dir = ROOT / "dataset_verified"
    (out_dir / "clean_train_list.txt").write_text("\n".join(train_paths), encoding="utf-8")
    (out_dir / "clean_val_list.txt").write_text("\n".join(val_paths), encoding="utf-8")
    (out_dir / "clean_test_list.txt").write_text("\n".join(test_paths), encoding="utf-8")
    (out_dir / "clean_kolhapur_test_list.txt").write_text("\n".join(kol_test_paths), encoding="utf-8")
    
    yaml_content = f"""path: {out_dir.as_posix()}
train: clean_train_list.txt
val: clean_val_list.txt
test: clean_test_list.txt

nc: 1
names: ['pothole']
"""
    (out_dir / "data_clean_single.yaml").write_text(yaml_content, encoding="utf-8")
    
    kol_yaml_content = f"""path: {out_dir.as_posix()}
train: clean_train_list.txt
val: clean_val_list.txt
test: clean_kolhapur_test_list.txt

nc: 1
names: ['pothole']
"""
    (out_dir / "data_clean_kolhapur.yaml").write_text(kol_yaml_content, encoding="utf-8")

    print("\nClean Dataset Lists created:")
    print(f"  Train entries:        {len(train_paths)} (includes {kol_train_count * 4} Kolhapur frames)")
    print(f"  Val entries:          {len(val_paths)}")
    print(f"  Test entries:         {len(test_paths)}")
    print(f"  Kolhapur test:        {len(kol_test_paths)}")
    print(f"  Excluded toxic/hung:  {excluded_count}")
    print(f"  Config YAML:          {out_dir / 'data_clean_single.yaml'}")

if __name__ == "__main__":
    main()
