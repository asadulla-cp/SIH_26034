# 🐛 Debug Mode Guide

## What is Debug Mode?

Debug mode enables **verbose logging** throughout the MetaLex system to help troubleshoot issues:

- **OCR Processing:** Shows detailed text detection, confidence scores, bounding boxes
- **Field Extraction:** Displays all candidate values and why specific values were chosen
- **Commodity Detection:** Shows keyword matches and confidence calculations
- **Rule Engine:** Logs each rule evaluation and why violations were triggered
- **API Requests:** Full request/response details

---

## ✅ How to Enable Debug Mode

### Method 1: Environment Variable (Recommended)

1. **Edit the `.env` file** in the project root:
   ```bash
   nano .env
   # or
   code .env
   ```

2. **Change `DEBUG_MODE` to `true`:**
   ```env
   DEBUG_MODE=true
   ```

3. **Restart the backend:**
   ```bash
   # Stop backend (Ctrl+C or kill the process)
   pkill -f uvicorn
   
   # Start fresh
   python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Check logs:**
   ```bash
   # Watch logs in real-time
   tail -f /tmp/metalex_backend.log
   ```

### Method 2: Command Line (Temporary)

```bash
# Stop existing backend
pkill -f uvicorn

# Start with debug mode
DEBUG_MODE=true python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: One-Line Quick Toggle

```bash
# Enable debug mode and restart
sed -i '' 's/DEBUG_MODE=false/DEBUG_MODE=true/' .env && \
pkill -f uvicorn && sleep 2 && \
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/metalex_backend.log 2>&1 &
echo "✅ Debug mode enabled - Check logs: tail -f /tmp/metalex_backend.log"
```

---

## 📊 What You'll See in Debug Mode

### Before Debug Mode (INFO level):
```
INFO:metalex:🚀 MetaLex v2 starting up...
INFO:metalex:✅ Database & Rule Engine initialized
INFO:metalex:Processing image 1/1: uploads/MLX-20260831-ABC123_0.jpg
INFO:     127.0.0.1:52398 - "POST /api/scan HTTP/1.1" 200 OK
```

### After Debug Mode (DEBUG level):
```
DEBUG:metalex:🐛 DEBUG MODE ENABLED - Verbose logging active
INFO:metalex:🚀 MetaLex v2 starting up...
DEBUG:metalex.ocr:Image quality assessment: blur=245.6, brightness=0.72, contrast=0.45
DEBUG:metalex.ocr:OCR detected 47 text blocks
DEBUG:metalex.ocr:Product name candidates: ['SORA', 'GLOBAL WRITINGS'], confidences: [0.87, 0.52]
DEBUG:metalex.ocr:MRP extraction: Found 2 candidates - ₹202 (0.95), Rs.200 (0.42)
DEBUG:metalex.ocr:Commodity detection: matches=['writings', 'pen'], category='stationery', confidence=0.85
DEBUG:rule_engine:Evaluating LM-PC-001 (Product Name): PASS
DEBUG:rule_engine:Evaluating LM-PC-003 (MRP Declaration): PASS (₹202)
DEBUG:rule_engine:Evaluating LM-PC-004 (Manufacturer): FAIL (value missing)
INFO:metalex:Inspection complete - Score: 72/100, Status: NON_COMPLIANT
INFO:     127.0.0.1:52398 - "POST /api/scan HTTP/1.1" 200 OK
```

---

## 🔍 Frontend Debug Mode (Browser Console)

The frontend already logs errors to the browser console. To see them:

1. **Open Developer Tools:**
   - Chrome/Edge: `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
   - Firefox: `F12` or `Ctrl+Shift+K` (Windows) / `Cmd+Option+K` (Mac)

2. **Go to Console tab**

3. **Look for:**
   - ❌ Red errors: `console.error()`
   - ⚠️ Yellow warnings: API failures, camera issues
   - ℹ️ Blue info: Network requests (check Network tab)

### Enable Verbose Network Logging:

1. Open DevTools → **Network** tab
2. Reload page
3. Click any API request (e.g., `POST /api/scan`)
4. View:
   - **Headers:** Request details
   - **Payload:** Uploaded data
   - **Response:** Backend response
   - **Preview:** Formatted JSON

---

## 🧪 Testing Debug Mode

### Test 1: Verify Debug Mode is Active

```bash
# Check backend logs for debug message
curl -s http://localhost:8000/api/health
grep "DEBUG MODE ENABLED" /tmp/metalex_backend.log
```

Expected output:
```
DEBUG:metalex:🐛 DEBUG MODE ENABLED - Verbose logging active
```

### Test 2: Scan with Verbose Logging

1. Open backend logs in terminal:
   ```bash
   tail -f /tmp/metalex_backend.log
   ```

2. Scan a product (camera or upload)

3. Watch logs scroll with detailed processing info

### Test 3: Check Frontend Console

1. Open http://localhost:5173
2. Open DevTools Console (F12)
3. Try to scan → any errors will show here

---

## 🎯 Common Debug Use Cases

### Issue: "Camera not working"
**Debug steps:**
1. ✅ Check browser console for camera permission errors
2. ✅ Look for `MediaDevices API not available` or `Permission denied`
3. ✅ Verify URL is `localhost` (not `127.0.0.1` or IP address)

### Issue: "OCR not detecting text"
**Debug steps:**
1. ✅ Enable backend debug mode
2. ✅ Check logs for: `OCR detected X text blocks`
3. ✅ If 0 blocks → image quality issue or OCR not loaded
4. ✅ Check: `"ocr_available": true` in `/api/health`

### Issue: "Wrong product name detected"
**Debug steps:**
1. ✅ Enable debug mode
2. ✅ Look for: `Product name candidates: [...]`
3. ✅ Shows why specific name was chosen (confidence, position)
4. ✅ Check annotated image (`/annotated/...jpg`) for bounding boxes

### Issue: "Database errors"
**Debug steps:**
1. ✅ Check logs for `sqlite3.OperationalError` or `IntegrityError`
2. ✅ Verify: `ls -lh metalex.db` (should exist)
3. ✅ Check columns: `sqlite3 metalex.db ".schema inspections"`

---

## 🔧 Advanced Debugging

### Python Interactive Debug (REPL)

```bash
# Start Python with backend loaded
python3

>>> from backend.services.ocr_pipeline import process_single_image
>>> result = process_single_image("uploads/test.jpg")
>>> print(result["fields"]["product_name"])
>>> result["quality"]
```

### SQLite Database Inspection

```bash
# Open database
sqlite3 metalex.db

# Check recent inspections
SELECT inspection_id, product_name, overall_status, compliance_score 
FROM inspections 
ORDER BY created_at DESC 
LIMIT 5;

# Check for errors
SELECT * FROM inspections WHERE overall_status = 'ERROR';

# Exit
.quit
```

### API Direct Testing (Skip Frontend)

```bash
# Test demo scan endpoint
curl -X POST http://localhost:8000/api/scan-demo-product/1 | python3 -m json.tool

# Test health
curl -s http://localhost:8000/api/health | python3 -m json.tool

# Test rules
curl -s http://localhost:8000/api/rules | python3 -m json.tool | head -20
```

---

## 🚨 Disable Debug Mode (For Demo/Production)

Debug mode generates **large log files** and slows down processing slightly.

### Quick Disable:

```bash
# Method 1: Edit .env file
sed -i '' 's/DEBUG_MODE=true/DEBUG_MODE=false/' .env

# Method 2: Stop and restart without DEBUG_MODE
pkill -f uvicorn
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📋 Debug Checklist

When troubleshooting issues, check:

- [ ] Backend running: `curl localhost:8000/api/health`
- [ ] Frontend running: `curl localhost:5173`
- [ ] Debug mode enabled: `grep "DEBUG MODE" /tmp/metalex_backend.log`
- [ ] Browser console open (F12 → Console)
- [ ] Network tab shows API requests
- [ ] Database exists: `ls -lh metalex.db`
- [ ] Uploads folder exists: `ls -lh uploads/`
- [ ] No permission errors in console
- [ ] Camera permission granted (if using camera)

---

## 🆘 Still Having Issues?

### Get Full Debug Output:

```bash
# Capture complete debug session
DEBUG_MODE=true python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee metalex_debug_full.log
```

Then scan your product and send the `metalex_debug_full.log` file.

---

## 📊 Log File Locations

- **Backend logs:** `/tmp/metalex_backend.log`
- **Frontend logs:** Browser DevTools Console
- **Database:** `metalex.db` (in project root)
- **Uploaded images:** `uploads/MLX-*.jpg`
- **Annotated images:** `annotated/MLX-*_annotated.jpg`
- **PDF reports:** `reports/MLX-*.pdf`

---

## ✅ Current Status

- **Debug Mode:** Currently `DISABLED` (set to `false` in `.env`)
- **To Enable:** Change `DEBUG_MODE=true` in `.env` and restart backend
- **Log Level:** INFO (production) → DEBUG (troubleshooting)

**Next:** Run the one-line command above to enable debug mode and test!
