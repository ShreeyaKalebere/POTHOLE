# Put the system online (works on any phone, laptop can be OFF)

**Result:** a link like `https://<your-name>-road-damage.hf.space` that opens the dashboard
and Live Patrol on any phone with mobile data. Real HTTPS, so camera + GPS work without warnings.

| Part | Service | Cost |
|---|---|---|
| Dashboard + backend + YOLO11 model | **Hugging Face Spaces** (Docker, 2 CPU, 16 GB RAM) | Free |
| Database + photos | **MongoDB Atlas** M0 cluster (512 MB) | Free |

Notes
- Runs on **CPU** in the cloud: about 5–10 frames/s instead of ~100 on your laptop GPU. Fine for photo upload and Live Patrol.
- A free Space **sleeps after 48 h without visitors**; the first visit after that takes ~1–2 min to wake up.
- Atlas free = 512 MB ≈ 3,000 detection photos. Clear demo data before the final demo.
- A **public** Space shows its code to anyone. The **dashboard itself is protected by the team password**.

---

## Step 1 — Database (MongoDB Atlas), ~10 min

1. Go to **mongodb.com/atlas** → sign up (free).
2. **Create cluster** → choose **M0 Free** → provider AWS, region **Mumbai (ap-south-1)** → Create.
3. **Database Access** → Add new database user → username e.g. `pothole_app`, **Autogenerate secure password** → copy it somewhere safe → role *Read and write to any database* → Add.
4. **Network Access** → Add IP address → **Allow access from anywhere (0.0.0.0/0)** → Confirm.
   (Needed because the cloud server's address changes. The database is still protected by the user/password.)
5. **Database → Connect → Drivers → Python** → copy the connection string. It looks like
   `mongodb+srv://pothole_app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   Replace `<password>` with the password from step 3. **Keep this string secret.**

## Step 2 — App (Hugging Face Space), ~15 min

1. On the laptop: `cd F:\POTHOLE_PROJECT\scripts` → `python make_hf_bundle.py`
   → creates `F:\POTHOLE_PROJECT\deploy\hf_space\` (≈ 20 MB).
2. Go to **huggingface.co** → sign up (free).
3. **New → Space** → name `road-damage` → SDK **Docker** → template **Blank** → hardware **CPU basic (free)** → visibility **Public** → Create Space.
4. **Files → Add file → Upload files** → drag **everything inside** `deploy\hf_space\`
   (the folders `backend`, `dashboard`, `deploy`, `models` and the files `Dockerfile`, `README.md`) → Commit.
5. **Settings → Variables and secrets → New secret**, add these three:

   | Name | Value |
   |---|---|
   | `MONGO_URI` | the connection string from Step 1 |
   | `APP_PASSWORD` | a team password you choose (share only with the team / guide) |
   | `APP_SECRET` | any long random text, e.g. 40 random letters and numbers |

6. The Space builds automatically (**~10 min** the first time; watch the *Logs* tab).
   When it shows **Running**, open `https://<your-name>-road-damage.hf.space`.

## Step 3 — Check it

1. Log in with the team password.
2. **Detect Damage** → upload a road photo → it should find damage and show it on the map.
3. On a phone (mobile data, not Wi-Fi): open the same link + `/live` → **Start patrol** → allow camera + location.
(The "Load demo incidents" button only works on the laptop — the dataset is not uploaded to the cloud.)

## Updating the model later
Train a new model → copy it to `models\final.pt` → run `python make_hf_bundle.py` →
in the Space upload the new `models/final.pt` → it rebuilds by itself.

## If something goes wrong
| Problem | Fix |
|---|---|
| Space log: `ServerSelectionTimeoutError` | `MONGO_URI` wrong, or Atlas Network Access not 0.0.0.0/0 |
| Login always says wrong password | check `APP_PASSWORD` secret (no spaces); restart the Space after changing secrets |
| Phone camera does not start | open the `https://...hf.space` link directly (not inside WhatsApp's built-in browser) |
| Very slow first load | Space was asleep — wait 1–2 min |
