import sys
import subprocess
import time
import urllib.request
import json

def verify():
    print("Launching Flask application server...")
    proc = subprocess.Popen([sys.executable, "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    
    try:
        # Check UI route
        req = urllib.request.urlopen("http://127.0.0.1:5000/")
        assert req.getcode() == 200
        html = req.read().decode("utf-8")
        assert "RailPredict" in html
        print("✓ UI Route [GET /]: 200 OK")
        
        # Check Corridors API
        req_corr = urllib.request.urlopen("http://127.0.0.1:5000/api/corridors")
        assert req_corr.getcode() == 200
        corr_data = json.loads(req_corr.read().decode("utf-8"))
        assert corr_data["status"] == "success"
        print(f"✓ Corridors API [GET /api/corridors]: OK ({len(corr_data['corridors'])} corridors loaded)")
        
        # Check Predict API
        payload = json.dumps({
            "corridor": "Delhi-Mumbai",
            "train_category": "Rajdhani/VB",
            "coach_class": "3A",
            "quota": "GNWL",
            "current_wl": 12,
            "lead_time_days": 20
        }).encode("utf-8")
        
        req_pred = urllib.request.Request(
            "http://127.0.0.1:5000/api/predict",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        res_pred = urllib.request.urlopen(req_pred)
        assert res_pred.getcode() == 200
        pred_data = json.loads(res_pred.read().decode("utf-8"))
        assert pred_data["status"] == "success"
        print(f"✓ Predict API [POST /api/predict]: OK (Probability: {pred_data['data']['probability_pct']}%, Tier: {pred_data['data']['risk_tier']})")
        
        # Check Metrics API
        req_met = urllib.request.urlopen("http://127.0.0.1:5000/api/metrics")
        assert req_met.getcode() == 200
        met_data = json.loads(req_met.read().decode("utf-8"))
        assert met_data["status"] == "success"
        print(f"✓ Metrics API [GET /api/metrics]: OK (RF Accuracy: {met_data['metrics']['random_forest']['accuracy']*100:.2f}%)")
        
        print("\nAll live HTTP server checks passed successfully!")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    verify()
