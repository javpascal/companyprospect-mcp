# Nummary ChatKit Playground

A modern, interactive web-based playground for testing and exploring Nummary APIs, inspired by ChatKit Studio.

## 🚀 Features

- **Modern Chat Interface**: Clean, responsive design with dark mode
- **Company Search**: Search for companies using natural language queries
- **Real-time API Integration**: Direct integration with Nummary APIs
- **Message History**: Keeps track of your conversation
- **Example Prompts**: Quick-start templates for common searches
- **Industry Analysis**: Analyze market trends and competitors
- **Export Functionality**: Export your search history as JSON

## 📋 Prerequisites

- Python 3.7+ with Flask
- Nummary API credentials (already configured in `config.py`)

## 🛠️ Installation

1. **Install Python dependencies**:
```bash
pip install flask flask-cors requests
```

2. **Verify API configuration**:
The API credentials are already configured in `config.py`:
- API URL: `https://api.nummary.co`
- API Key and User ID are pre-configured

## 🎮 Usage

### Step 1: Start the Backend Server

Open a terminal and run:
```bash
python playground_server.py
```

The server will start on `http://localhost:5000` and display:
- Available endpoints
- Server configuration
- Health check status

### Step 2: Open the Playground

Open `nummary_playground.html` in your web browser:
- **Option 1**: Double-click the file to open in your default browser
- **Option 2**: Open via terminal:
  ```bash
  open nummary_playground.html  # macOS
  xdg-open nummary_playground.html  # Linux
  start nummary_playground.html  # Windows
  ```

### Step 3: Start Searching!

Try these example queries:
- "Search for AI companies"
- "Find fintech startups"
- "Show me companies similar to Factorial"
- "Search for e-commerce platforms"
- "Find healthcare technology companies"

## 🔧 API Endpoints

The playground server provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/nummary/search` | POST | Search for companies |
| `/api/nummary/company/<id>` | GET | Get company details |
| `/api/nummary/analyze` | POST | Analyze industry trends |
| `/api/history` | GET | Get search history |
| `/api/history` | DELETE | Clear search history |
| `/api/export` | GET | Export conversation data |
| `/api/suggestions` | POST | Get search suggestions |
| `/health` | GET | Server health check |

## 🎨 Customization

### Changing the Port

Edit `playground_server.py`:
```python
port = int(os.environ.get('PORT', 5000))  # Change 5000 to your desired port
```

Then update the API URL in `nummary_playground.html`:
```javascript
const response = await fetch('http://localhost:5000/api/nummary/search', {
    // Change 5000 to match your server port
```

### Adding Custom Styles

The playground uses CSS variables for theming. You can customize colors in the `<style>` section of `nummary_playground.html`:

```css
:root {
    --bg-primary: #0f0f0f;
    --accent: #6366f1;
    /* Add your custom colors here */
}
```

## 🚀 Deployment Options

### Local Development
Already configured - just run the server and open the HTML file.

### Production Deployment

1. **Update API endpoint in playground HTML**:
   Replace `http://localhost:5000` with your production server URL

2. **Deploy server to cloud platform**:
   - **Heroku**: Use the included `Procfile`
   - **Railway**: Use the included `railway.json`
   - **Vercel**: Use the included `vercel.json`

3. **Enable HTTPS**: 
   Update the fetch URLs to use `https://` in production

## 🔍 Troubleshooting

### "Cannot connect to server" error
- Ensure the backend server is running: `python playground_server.py`
- Check that port 5000 is not blocked by firewall
- Verify the server URL matches in both files

### No search results
- Check API credentials in `config.py`
- Verify network connectivity
- Check server logs for error messages

### CORS issues
- The server has CORS enabled by default
- If issues persist, check browser console for specific CORS errors

## 📊 API Response Format

### Successful Search Response:
```json
{
  "success": true,
  "data": [
    {
      "name": "Company Name",
      "description": "Company description",
      "industry": "Technology",
      "location": "San Francisco, CA",
      "employees": "100-500",
      "founded": "2020"
    }
  ],
  "count": 1,
  "query": "original search query"
}
```

### Error Response:
```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

## 📝 License

This playground is built for testing and development with the Nummary API.

## 🤝 Support

For issues with:
- **Playground**: Check this README or modify the code as needed
- **Nummary API**: Contact Nummary support
- **Server issues**: Check server logs in the terminal

---

Built with ❤️ for exploring Nummary APIs
