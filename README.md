# 🚦 SafeSight AI — Traffic Sign Visibility Analyzer

> 🚀 AI-powered system for real-time highway safety monitoring and traffic sign visibility analysis

---

## ✨ Features

* 🎬 **Video Processing** – Analyze recorded footage and export annotated videos
* 📷 **Live Camera Feed** – Real-time detection with GPS logging
* 🖼 **Image Analysis** – Batch processing for visibility scoring
* 📍 **GPS Integration** – Logs coordinates of detected signs
* 📊 **CSV Logging** – Generates structured reports
* 🌓 **Day/Night Optimization** – CLAHE enhancement for low light
* 🎯 **Visibility Classification** – 🔴 Poor | 🟡 Moderate | 🟢 Good

---

## 🧠 Visibility Calculation Logic

### 📐 Formula

```text
Visibility Score = Mean(Intensity of Top 15% Brightest Pixels) / 255.0
```

### 📊 Classification

| Score Range | Condition   | Meaning                            |
| ----------- | ----------- | ---------------------------------- |
| ≥ 0.65      | 🟢 GOOD     | Highly reflective, clearly visible |
| 0.45 – 0.65 | 🟡 MODERATE | Degrading, needs attention         |
| < 0.45      | 🔴 POOR     | Critical, faded or non-reflective  |

---

## 🖼️ Visual Samples

<table align="center">
<tr>
<td align="center">
<img src="samples/1.jpg" width="350"><br>
<b>Sample 1</b>
</td>
<td align="center">
<img src="samples/2.jpg" width="350"><br>
<b>Sample 2</b>
</td>
</tr>

<tr>
<td align="center">
<img src="samples/3.jpg" width="350"><br>
<b>Sample 3</b>
</td>
<td align="center">
<img src="samples/4.jpg" width="350"><br>
<b>Sample 4</b>
</td>
</tr>
</table>

---

## ⚙️ Installation

```bash
git clone https://github.com/mpnithishpraba/SafeSight_AI-Traffic-Sign-Visibility-Analyzer.git
cd SafeSight_AI-Traffic-Sign-Visibility-Analyzer
pip install -r requirements.txt
```

---

## 🚀 Run the Application

```bash
python app.py
```

---

## 📂 Project Structure

```bash
SafeSight-AI/
├── app.py
├── core/
├── models/
│   └── best.pt
├── utils/
├── logs/
├── detections/
└── samples/
```

---

## 📊 Model Performance

| Metric    | Value |
| --------- | ----- |
| Precision | 94.9% |
| Recall    | 75%   |
| mAP@50    | 85.3% |
| mAP@50-95 | 57%   |

✔ High precision
⚠️ Recall can improve for distant/small signs

---

## 🚀 Scalability

* 📁 **Seamless Workspaces**
  Auto-generates session folders for logs and outputs

* ⚡ **Batch Processing**
  Process thousands of images for large-scale audits

* 🔧 **Modular Architecture**
  YOLO model can be retrained or replaced easily

---

## 💰 Cost Effective

* ❌ No cloud or API costs
* 💻 Runs completely offline
* ⚙️ Works on standard laptops
* 🔓 Built on open-source AI

---

## 🌱 Sustainability

* 🚗 Reduces need for survey vehicles
* ♻️ Minimizes material waste
* 🔍 Enables targeted maintenance
* 🌍 Energy-efficient offline processing

---

## 🚀 Future Improvements

* Improve recall (small & distant signs)
* Expand dataset (2000+ images)
* Edge deployment (Jetson / Raspberry Pi)
* Cloud monitoring dashboard
* Multi-class traffic sign detection

---

## ⭐ Support

If you like this project:

👉 Star the repository
👉 Share it
👉 Contribute improvements

