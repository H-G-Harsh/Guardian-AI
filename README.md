# Guardian - Slack Parental Monitoring App

A Streamlit-based web application that provides parental monitoring capabilities for Slack channels. Guardian helps parents monitor their child's Slack communications for safety by scanning messages in real-time and alerting parents to suspicious or predatory content.

## Features

- 🛡️ **Real-time monitoring** of Slack messages
- 📧 **Instant email alerts** for suspicious content
- 🤖 **AI-powered detection** of predatory behavior
- 📊 **Live dashboard** showing scan results
- 🔧 **Easy configuration** through web interface
- 💾 **State persistence** across sessions

## Quick Start

### Prerequisites

- Python 3.8+
- Slack workspace access
- Portia API key
- Email service access (via Portia Google integration)

### Installation

1. **Clone or download the project files**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file with the following variables:
   ```env
   PORTIA_API_KEY=your_portia_api_key_here
   SLACK_CHANNEL_ID=your_slack_channel_id_here
   PARENT_EMAIL=parent@example.com
   ```

4. **Run the application:**
   ```bash
   python agent.py
   ```

5. **Set up Slack API bot and Portia Cloud API:**
   - Create a Slack API bot with OAuth scopes: `channels:read` and `users:read`
   - Connect your Portia Cloud API on the dashboard
   - Ensure proper authentication is configured


## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PORTIA_API_KEY` | Your Portia Cloud API key | `pk_live_...` |
| `SLACK_CHANNEL_ID` | Slack channel ID to monitor | `C1234567890` |
| `PARENT_EMAIL` | Email for receiving alerts | `parent@example.com` |

### Getting Your Slack Channel ID

1. Open Slack in your browser
2. Navigate to the channel you want to monitor
3. Look at the URL - the channel ID is the part after `/messages/`
4. Example: `https://app.slack.com/client/T.../C1234567890` → Channel ID is `C1234567890`

### Getting Your Portia API Key

1. Sign up at [Portia Cloud](https://portia.ai)
2. Create a new project
3. Generate an API key from your project dashboard
4. Copy the key to your `.env` file



### Understanding Results

- ✅ **Safe**: No concerning content detected
- ⚠️ **Suspicious**: Potentially concerning content found
- 🚨 **Predatory**: High-risk content detected (immediate alert sent)

## Email Alerts

When suspicious or predatory content is detected:

1. **Immediate notification** sent to configured parent email
2. **Detailed information** including message content, sender, and timestamp
3. **Severity level** indication (suspicious vs predatory)
4. **HTML formatted** for easy reading

## Troubleshooting

### Common Issues

**"Configuration incomplete" error:**
- Verify all environment variables are set in `.env`
- Check that your Portia API key is valid
- Ensure Slack channel ID is correct

**"Failed to start monitoring" error:**
- Check your internet connection
- Verify Portia API key has sufficient credits
- Ensure Slack channel is accessible

**Email alerts not received:**
- Check spam/junk folder
- Verify parent email address is correct
- Ensure Portia Google integration is configured

**App won't start:**
- Install all dependencies: `pip install -r requirements.txt`
- Check Python version (3.8+ required)
- Verify `.env` file exists and is properly formatted

### Logs

Application logs are saved to `guardian_app.log` for debugging purposes.

### State Recovery

The app automatically saves your progress and can recover from interruptions:
- Configuration settings are preserved
- Page navigation state is maintained
- Monitoring status is restored when possible

