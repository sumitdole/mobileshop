# Shop Manager — Android App (Phase 1)

A standalone Android version of the shop app, built with Kivy/KivyMD.
It has its own local SQLite database on the phone (does **not** share
data with the Windows desktop app yet — see "About syncing" below).

## Important: I could not test-run this one

I wasn't able to install Kivy in the sandbox I build in, so this code
is **syntax-checked but not runtime-tested**. It follows standard,
well-documented KivyMD 1.1.x patterns, but expect at least a small bug
on first run — that's normal for a UI framework I couldn't execute
myself. Report back exactly what breaks and I'll fix it fast.

## What's included (Phase 1 — same scope as desktop Phase 1)

- **Dashboard** — today's sales/profit, low stock, pending credit, quick actions
- **Billing** — search & add products, adjust quantity, pick a customer,
  Cash/UPI/Card/Credit payment, saves the bill and shows a text receipt
  you can **Share** via WhatsApp/SMS/etc.
- **Products** — search, add, edit, delete
- **Customers** — search, add, view purchase history & credit balance,
  record credit payments
- **Inventory** — stock list (low-stock items sorted to the top), tap to
  make a manual adjustment

**Not included yet:** Suppliers, Purchases, Expenses, Returns, Reports,
Analytics, Bill History, login/roles, and PDF invoices (this phone
version shares a plain-text receipt instead — see the note at the top
of `screens/billing.py` for why).

## About syncing with the desktop app

This phone app is fully standalone right now — bills made here don't
appear on the desktop app and vice versa. The database schema
intentionally matches the desktop app's tables (down to column names),
plus a couple of sync-friendly fields (`bills.synced`, a `device_info`
table), so syncing later won't require redoing the data model on either
side. Mobile invoice numbers are prefixed `MINV-` so they're
distinguishable from desktop `INV-` numbers until sync unifies them.

## Step 1 — Try it on your PC first (fast feedback loop)

Before building the APK (which takes 20–45 minutes), run it as a
regular desktop window to catch obvious bugs in seconds. You already
did this with `py -3.11` — keep using that:

```
py -3.11 -m pip install -r requirements.txt
py -3.11 main.py
```

Click through every screen. This step catches most issues far faster
than a full Android build cycle.

## Step 2 — Build the APK using Google Colab

This is the path we're using — **no Ubuntu, no WSL, no local install**
of any Android tooling. Everything builds on Google's free servers.

1. **Zip this folder.** On Windows: right-click the `shop_mobile`
   folder → Send to → Compressed (zipped) folder. You should get
   `shop_mobile.zip` with `buildozer.spec`, `main.py`, etc. directly
   inside it (not nested another folder deeper).

2. **Open the notebook.** Go to https://colab.research.google.com →
   File → Upload notebook → select `ShopManager_Build_APK.ipynb`
   (included in this folder). Sign in with a Google account if asked.

3. **Run the cells in order**, top to bottom — click the ▶ button on
   each cell, or use Runtime → Run all:
   - **Cell 1** installs build tools (a few minutes).
   - **Cell 2** prompts you to upload `shop_mobile.zip` — pick it from
     your PC when the file picker appears.
   - **Cell 3** unzips and locates the project.
   - **Cell 4** is the actual build — **20–45 minutes the first time**
     (it downloads the Android SDK/NDK, several GB). Keep the tab open;
     Colab free tier disconnects after long idle periods, but active
     building counts as activity, so this is usually fine.
   - **Cell 5** finds the finished `.apk` and downloads it straight to
     your PC's Downloads folder.

4. **If Cell 4 fails**, scroll up through its output (not just the
   last line) to find the actual error, copy the last ~20-30 lines, and
   send them to me — Android build failures are almost always one
   specific, fixable thing.

## Step 3 — Install it on your phone

Transfer the downloaded `.apk` to your Android phone any way that's
convenient (Google Drive, email to yourself, WhatsApp to yourself, USB
cable) and tap it to install. Android will warn about "install from
unknown sources" since it's not from the Play Store — that's expected;
allow it for this file.

## Rebuilding after a code change

Colab doesn't remember your project between sessions on the free tier.
To build again after I send you an updated `shop_mobile`, just re-zip
the updated folder and repeat Step 2 with a fresh notebook run.

## Other build options (if you ever want them)

- **GitHub Actions** — push this project to a GitHub repo and it builds
  automatically in the cloud on every push, no browser babysitting
  required. The workflow file is already included at
  `.github/workflows/build-apk.yml`. Ask me if you want the setup steps
  for this later — Colab is simpler to start with.
- **WSL2 (Ubuntu on your own PC)** — lets you build repeatedly without
  depending on any cloud service. More setup up front, faster to
  iterate once it's working. Ask if you'd like these steps.

## Data safety

The phone's database lives in the app's private storage — uninstalling
the app deletes it. There's no backup/export screen on the phone yet
(Phase 2, along with the other missing modules above). Until then,
treat the desktop app as your source of truth and use the phone app for
quick on-the-go billing only.
