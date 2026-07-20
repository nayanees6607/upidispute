# 💳 UPI Dispute Management System

A full-stack web application that streamlines the process of raising, tracking, and resolving UPI payment disputes. The system enables users to report failed or incorrect UPI transactions while allowing administrators to efficiently review, manage, and resolve disputes through a centralized dashboard.

---

## 🚀 Features

### 👤 User
- User Registration & Login
- Secure Authentication
- Raise a New UPI Dispute
- Upload Transaction Details
- Track Dispute Status
- View Dispute History
- Update Profile

### 👨‍💼 Admin
- Secure Admin Login
- View All Disputes
- Update Dispute Status
- Assign Priority
- Resolve or Reject Disputes
- Dashboard with Statistics
- Manage Users

---

## 🛠 Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap

### Backend
- Node.js
- Express.js

### Database
- MongoDB

### Tools
- Git
- GitHub
- VS Code
- Postman

---

## 📂 Project Structure

```
UPIDispute/
│
├── backend/
│   ├── controllers/
│   ├── routes/
│   ├── models/
│   ├── middleware/
│   └── server.js
│
├── frontend/
│   ├── css/
│   ├── js/
│   ├── images/
│   └── pages/
│
├── package.json
├── README.md
└── .env
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/nayanees6607/upidispute.git
```

Move into the project folder

```bash
cd upidispute
```

Install dependencies

```bash
npm install
```

Create a `.env` file

```env
PORT=5000
MONGO_URI=your_mongodb_connection_string
JWT_SECRET=your_secret_key
```

Start the server

```bash
npm start
```

or

```bash
node server.js
```

---

## 📷 Screenshots

Add screenshots of:

- Home Page
- Login Page
- User Dashboard
- Raise Dispute Page
- Admin Dashboard
- Dispute Tracking Page

---

## 🔄 Workflow

1. User logs in.
2. User raises a dispute.
3. Transaction details are stored in MongoDB.
4. Admin reviews the dispute.
5. Admin updates the dispute status.
6. User tracks the dispute until resolution.

---

## 📌 Future Enhancements

- OTP Verification
- Email Notifications
- SMS Alerts
- AI-based Fraud Detection
- Razorpay/UPI API Integration
- Analytics Dashboard
- Mobile Application
- Chat Support

---

## 🧪 Testing

- User Authentication
- API Testing using Postman
- Form Validation
- Database Operations
- Admin Functionalities

---

## 🤝 Contributors

- Nayanees
- Team Members

---

## 📄 License

This project is developed for educational purposes.

---

## ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub.
