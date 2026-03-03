# Strava Bike Dashboard

A local dashboard that connects to your Strava account and displays mileage, elevation gain, and moving time for each of your bikes. Filter by date range and metric type.

## Prerequisites

- Python 3.8+
- A Strava account

## 1. Register a Strava API Application

1. Go to <https://www.strava.com/settings/api>
2. Fill in:
   - **Application Name**: anything you like (e.g. "My Bike Dashboard")
   - **Category**: choose any
   - **Website**: `http://localhost`
   - **Authorization Callback Domain**: `localhost`
3. After saving, note your **Client ID** and **Client Secret**

## 2. Configure Credentials

Open the `.env` file in this folder and replace the placeholder values with your real credentials:

```
STRAVA_CLIENT_ID=12345
STRAVA_CLIENT_SECRET=abc123def456...
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open at **http://localhost:8501**. Click **Connect with Strava** to authorize, and your bike data will appear.
