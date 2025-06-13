# YouTube Media Downloader

A Streamlit application that allows you to download YouTube videos and audio in various formats and qualities.

## Features
- Download videos as MP4 or audio as MP3
- Multiple quality options
- Search functionality
- Direct URL download
- Mobile-friendly interface

## Deployment Instructions

1. Create a GitHub account if you don't have one
2. Create a new repository on GitHub
3. Push this code to your repository
4. Go to [Streamlit Cloud](https://streamlit.io/cloud)
5. Sign up/Login with your GitHub account
6. Click "New app"
7. Select your repository
8. Set the main file path as `ytdownloader.py`
9. Click "Deploy"

## Local Development
To run locally:
```bash
pip install -r requirements.txt
streamlit run ytdownloader.py
```

## Note
This application requires yt-dlp to be installed on the server. Streamlit Cloud will handle this automatically through the requirements.txt file. 