# 📸 Camera Troubleshooting Guide

## ✅ Database Issue FIXED
- Backend restarted with correct database schema
- Backend running at: http://localhost:8000
- Database has commodity columns: ✓

---

## 🎥 How to Test Camera Feature

### Step 1: Open Browser Console
1. Open http://localhost:5173/camera in Chrome/Firefox
2. Press `F12` to open Developer Tools
3. Go to **Console** tab
4. Look for any red errors

### Step 2: Check Camera Permissions
- Browser will ask: **"localhost wants to use your camera"**
- Click **"Allow"** or **"Yes"**
- If you clicked "Block" before, you need to reset permissions:
  - Chrome: Click the 🔒 or camera icon in address bar → Reset permissions
  - Firefox: Click the 🔒 icon → Clear permissions

### Step 3: Common Issues

#### ❌ "Camera not available" or "Permission denied"
**Cause:** Browser blocked camera access

**Fix:**
1. Check address bar for camera icon (🎥 with X)
2. Click it and select "Allow"
3. Refresh page

#### ❌ Camera shows black screen
**Cause:** Wrong camera selected or driver issue

**Fix:**
1. Close all other apps using camera (Zoom, Teams, etc.)
2. Refresh browser
3. Try different browser (Chrome works best)

#### ❌ "MediaDevices API not available"
**Cause:** Not using HTTPS or localhost

**Fix:**
- Make sure URL is exactly: `http://localhost:5173/camera`
- NOT: `http://127.0.0.1` or `http://your-ip`

#### ❌ Nothing happens when clicking "Capture Image"
**Cause:** Camera state not active

**Fix:**
1. Wait for green "Camera Active" badge in top right
2. If stuck on "Requesting Access", refresh page
3. Check console for JavaScript errors

---

## 🔍 Debug Steps

### Test 1: Check if camera is detected
Open browser console and run:
```javascript
navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    const cameras = devices.filter(d => d.kind === 'videoinput');
    console.log('Cameras found:', cameras.length);
    cameras.forEach(c => console.log(c.label));
  });
```

### Test 2: Manual camera access
```javascript
navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    console.log('✓ Camera access granted');
    stream.getTracks().forEach(track => track.stop());
  })
  .catch(err => console.error('✗ Camera error:', err));
```

---

## 🚀 Expected Behavior

1. **On page load:**
   - "Requesting Access" status
   - Browser permission prompt appears
   - After allowing: "Camera Active" with green dot

2. **When capturing:**
   - Click "Capture Image" button
   - Image appears in preview grid on right
   - Counter updates: "1/5 images captured"
   - Can capture up to 5 images

3. **When submitting:**
   - Click "Scan X Images" button
   - Processing indicator: "Processing X images..."
   - Redirects to inspection detail page
   - Shows compliance results

---

## 🖼️ Alternative: Use File Upload Instead

If camera doesn't work, you can still test with the file upload:

1. Go to http://localhost:5173/scan
2. Click "Choose Files" or drag & drop
3. Select image from your phone/computer
4. Click "Scan Package"

---

## 🔧 Quick Fix Script

Run this in your terminal to restart everything fresh:

```bash
# Stop all processes
pkill -f uvicorn
pkill -f "npm run dev"
sleep 2

# Start backend
cd /Users/namangaur/SIH_26034
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

# Start frontend
cd frontend
npm run dev &

# Wait and test
sleep 4
echo "✓ Servers started"
echo "Open: http://localhost:5173/camera"
```

---

## 📱 Mobile Testing

### iOS Safari:
- Must use HTTPS (not http)
- Or use ngrok tunnel: `ngrok http 5173`
- Camera permission is per-site

### Android Chrome:
- Works with http://localhost if testing locally
- Or use USB debugging with Chrome DevTools

---

## ✅ Verification Checklist

- [ ] Backend running at :8000 (check `/api/health`)
- [ ] Frontend running at :5173
- [ ] Browser is Chrome/Firefox/Edge (not IE)
- [ ] URL is exactly `http://localhost:5173/camera`
- [ ] Camera permission granted (no block icon)
- [ ] No other app using camera
- [ ] Console shows no red errors
- [ ] Green "Camera Active" badge visible

---

## 🆘 Still Not Working?

### Option 1: Check browser console
Send me screenshot of console errors (F12 → Console tab)

### Option 2: Use file upload
The file upload at `/scan` works identically - same backend, same results

### Option 3: Test with demo
Use demo products on dashboard - they work without camera

---

**Current Status:**
- ✅ Backend: Running & Fixed
- ✅ Frontend: Running
- ✅ Database: Has commodity columns
- ❓ Camera: Needs browser testing

**Next Step:** Open http://localhost:5173/camera and check console for errors
