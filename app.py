import os
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import re
import firebase_admin
from firebase_admin import credentials, firestore
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# 🔒 Load API Keys from Environment Variables (Recommended)
YOUTUBE_API_KEY = "AIzaSyC7cqLOADQ68Kr_KACt5m-5SXQaq7Xtrbs"
GEMINI_API_KEY = "AIzaSyC7cqLOADQ68Kr_KACt5m-5SXQaq7Xtrbs"

# ✅ Initialize Firebase Firestore
cred = credentials.Certificate("firebase_credentials.json")  # Ensure this file is downloaded from Firebase
firebase_admin.initialize_app(cred)
db = firestore.client()

# 📌 Function to extract Video ID from any YouTube URL
def extract_video_id(url):
    patterns = [
        r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# 🎬 Function to fetch video transcript
def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript])
        return transcript_text
    except Exception:
        return None  # Return None if transcript is not available

# 🤖 Function to summarize text using Gemini AI
def summarize_text(text):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": f"Summarize this: {text}"}]}]
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        summary = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return summary
    return None  # Return None if summary fails

# 🔥 Function to save summaries in Firebase Firestore
def save_summary(video_id, summary):
    doc_ref = db.collection("summaries").document(video_id)
    doc_ref.set({"summary": summary})
    print(f"✅ Summary saved for Video ID: {video_id}")

# 📌 API Route
@app.route('/summarize', methods=['POST'])
def summarize_video():
    data = request.json
    video_url = data.get('video_url')
    
    # ✅ Extract Video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    # ✅ Fetch Transcript
    transcript = get_video_transcript(video_id)
    if not transcript:
        return jsonify({"error": "Transcript not available"}), 400
    
    # ✅ Generate Summary
    summary = summarize_text(transcript)
    if not summary:
        return jsonify({"error": "Error summarizing transcript"}), 500
    
    # ✅ Save in Firebase Firestore
    save_summary(video_id, summary)

    return jsonify({"video_id": video_id, "summary": summary})

if __name__ == "__main__":
    app.run(debug=True)
