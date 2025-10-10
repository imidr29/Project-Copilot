# Token Counter Integration Guide

## 🎯 How to Use the Token Counter in Your Webapp

### **1. Start the Backend Server**
```bash
cd /home/hackysapy/hope/Wingardium-RavaDosa/backend
python3 main.py
```

### **2. Get Your API Token**
When the server starts, look for these log messages:
```
✅ Default tokens created
Admin token: [your_admin_token_here]
User token: [your_user_token_here] 
Readonly token: [your_readonly_token_here]
```

### **3. Start the Frontend**
```bash
cd /home/hackysapy/hope/Wingardium-RavaDosa/frontend/ops-copilot-frontend
ng serve
```

### **4. Use the Web Interface**

1. **Open your browser** to `http://localhost:4200`

2. **Enter your token** in the header:
   - You'll see a token input field at the top
   - Paste your token (start with `user` token for regular use)
   - Click "Set Token" or press Enter

3. **See the token counter**:
   - Once you set a token, the token counter will appear
   - It shows your usage statistics, daily limits, and token info

4. **Make API calls**:
   - Use the chat interface normally
   - Each query will be tracked in the token counter
   - You'll see your usage increase in real-time

### **5. What You'll See**

#### **Token Counter Display:**
- **User Stats**: Your total requests, daily requests, token count
- **Usage Bar**: Visual progress bar showing daily usage (100 request limit)
- **Token List**: All your tokens with individual usage counts
- **System Stats**: (Admin only) System-wide analytics

#### **Real-time Updates:**
- Usage counts update with each API call
- Progress bar changes color as you approach limits
- Token information refreshes automatically

### **6. Token Types**

- **User Token**: Best for regular use - full API access
- **Admin Token**: For system administration - can see all users' stats
- **Readonly Token**: For monitoring - limited access

### **7. Features**

✅ **Real-time tracking** - See usage update with each query
✅ **Visual indicators** - Progress bars and color coding
✅ **Token management** - View all your tokens and their usage
✅ **Rate limiting** - 100 requests per hour per token
✅ **Daily reset** - Counters reset automatically
✅ **Role-based access** - Different views for different user types

### **8. Troubleshooting**

**Token not working?**
- Check server logs for the actual token
- Make sure you copied the full token
- Try the "user" token first

**Token counter not showing?**
- Make sure you've set a token in the header
- Check browser console for errors
- Verify the backend is running

**API calls failing?**
- Check if your token is valid
- Look at server logs for authentication errors
- Try refreshing the page

### **9. Example Usage**

1. Start server → Get tokens from logs
2. Start frontend → Open browser
3. Enter token → See counter appear
4. Make queries → Watch usage increase
5. Check limits → See progress bar fill up

The token counter is now fully integrated into your webapp and will show real-time usage statistics as you use the API!
