
# ☁️ CloudBox - Cloud File Storage

A cloud-based file storage web application built using Python Flask and Supabase.

## 🌐 Live Demo

https://cloudbox-x505.onrender.com

## ✨ Features

- User Registration and Login
- Email Verification
- Secure Authentication
- Upload Files
- Download Files
- Delete Files
- Private Cloud Storage
- User-wise File Isolation
- Dashboard Interface

## 🛠️ Technologies Used

- Python
- Flask
- HTML
- CSS
- Supabase
- Git and GitHub
- Render

## 📂 Supported File Formats

- PDF
- PNG
- JPG
- JPEG
- TXT
- DOCX
- XLSX
- CSV

Maximum file size: 5 MB.

## 🏗️ Project Architecture

User
  ↓
CloudBox Frontend
  ↓
Flask Backend
  ↓
Supabase Authentication
  ↓
Supabase Cloud Storage

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone YOUR_REPOSITORY_URL
```

### 2. Open Project Folder

```bash
cd cloudbox
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Environment

```bash
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a `.env` file.

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

Never upload real API keys or secrets to GitHub.

### 7. Run Project

```bash
python app.py
```

Open http://127.0.0.1:5000

## 🔐 Security

- Private Supabase Storage
- User-wise file isolation
- Authentication protected operations
- Environment-based secret configuration

## 🚀 Future Improvements

- Storage Usage Analytics
- File Search
- File Sharing
- User Profile Management

## 👨‍💻 Developer

CloudBox - Cloud Computing Project

Built using Python Flask and Supabase.
