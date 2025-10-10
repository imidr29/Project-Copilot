# Frontend Token Counter Debug Guide

## 🔍 How to See the Token Counter

### **1. Start the Frontend**
```bash
cd /home/hackysapy/hope/Wingardium-RavaDosa/frontend/ops-copilot-frontend
ng serve
```

### **2. Open Browser**
Go to `http://localhost:4200`

### **3. What You Should See**

#### **Without Token:**
- Header with "OEE Co-Pilot" title
- Token input field with "Enter your API token" placeholder
- **Token Counter section** with:
  - "🔐 Token Counter" heading
  - "Enter your API token above to see usage statistics" message
  - Debug info showing "Token Status: Not Set"

#### **With Token:**
- Header showing your token (first 8 characters + "...")
- **Token Counter section** showing:
  - Your usage statistics
  - Progress bars
  - Token information

### **4. Debug Steps**

#### **Check Browser Console:**
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for these messages:
   - "App initialized - Token status: Not Set"
   - "TokenCounter initialized with token: None"
   - When you set a token: "Setting token: abc12345..."

#### **Check Network Tab:**
1. Go to Network tab in Developer Tools
2. Set a token and make a query
3. Look for API calls to `/api/usage/stats`
4. Check if they have Authorization headers

#### **Check Elements Tab:**
1. Look for elements with class `token-counter-section`
2. Check if `app-token-counter` component is present
3. Verify the token input field is working

### **5. Common Issues & Solutions**

#### **Token Counter Not Visible:**
- Check if you see the dashed border box with "🔐 Token Counter"
- If not, check browser console for errors
- Make sure Angular is running without errors

#### **Token Not Working:**
- Check server logs for actual tokens
- Make sure you copied the full token
- Check browser console for API errors

#### **Component Not Loading:**
- Check if there are any TypeScript compilation errors
- Make sure all imports are correct
- Check if the component is properly declared

### **6. Manual Test Steps**

1. **Load the page** - You should see the token counter section
2. **Enter a token** - Click "Set Token" button
3. **Check console** - Should see "Token set" messages
4. **Make a query** - Use the chat interface
5. **Check usage** - Should see usage statistics update

### **7. Expected Behavior**

- **Page loads**: Token counter section is visible
- **No token**: Shows "Enter your API token above" message
- **Token set**: Shows usage statistics and progress bars
- **API calls**: Usage counts increase with each query
- **Console logs**: Shows debugging information

### **8. If Still Not Working**

1. **Check Angular compilation**:
   ```bash
   ng build --watch
   ```

2. **Check for errors**:
   ```bash
   ng serve --verbose
   ```

3. **Clear browser cache** and reload

4. **Check if backend is running** on port 8000

The token counter should now be **always visible** on the page, making it easy to see and debug!
