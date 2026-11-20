# ☁️ CloudBox – Cloud-Based File Storage System

CloudBox is a secure, web-based cloud file storage application that allows users to upload, store, download, rename, and delete their files anytime through the internet.

🌐 **Live Demo:** https://cloudbox-x505.onrender.com

## ✨ Features

- User Registration and Login
- Email Verification
- Secure User Authentication
- Cloud File Upload and Download
- Rename and Delete Files
- Private Cloud Storage
- User-wise File Isolation
- File Type Validation
- Maximum 5 MB File Upload
- Storage Management
- User-friendly Dashboard

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend Programming |
| Flask | Web Framework |
| HTML5 | Frontend Structure |
| CSS3 | Website Styling |
| JavaScript | Frontend Interactions |
| Supabase | Authentication and Cloud Storage |
| Render | Application Deployment |
| Git & GitHub | Version Control |

## 📂 Supported File Formats

- PDF
- PNG
- JPG / JPEG
- TXT
- DOCX
- XLSX
- CSV

**Maximum file size:** 5 MB per file.

## 🏗️ Project Architecture

```text
User
  |
  v
CloudBox Frontend
  |
  v
Flask Backend
  |
  v
Supabase Authentication
  |
  v
Supabase Private Storage
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### 2. Open the Project Folder

```bash
cd YOUR_PROJECT_FOLDER
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

For Windows:

```bash
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a `.env` file in the project root directory.

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FLASK_SECRET_KEY=your_secret_key
CALLBACK_URL=http://127.0.0.1:5000/auth/callback
```

Replace the example values with your actual configuration.

**Important:** Never upload your actual `.env` file, API keys, or secret keys to GitHub.

### 7. Run the Application

```bash
python app.py
```

Open your browser and visit:

http://127.0.0.1:5000

## 🔐 Security Features

- Supabase Private Storage Bucket
- User-specific File Storage
- Authentication-protected Operations
- CSRF Protection
- File Extension Validation
- Environment-based Secret Configuration

## 🚀 Future Improvements

- File Sharing Through Secure Links
- Storage Usage Analytics
- Advanced File Search
- Folder Management
- File Preview
- AWS S3 Integration
- Two-Factor Authentication

## 👨‍💻 Developer

**Project:** CloudBox – Cloud-Based File Storage System

**Category:** Cloud Computing / Web Development

**Built With:** Python, Flask, Supabase and Render

---

⭐ If you find this project interesting, consider giving the repository a star!