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
flowchart TD
    A([🚀 User Opens UPI Dispute System]) --> B[🔐 Register / Login]

    B --> C{Authentication Successful?}

    C -- No --> B
    C -- Yes --> D[👤 User Dashboard]

    D --> E[📝 Raise UPI Dispute]
    E --> F[💳 Enter Transaction Details]
    F --> G[📎 Upload Supporting Details]
    G --> H[(🗄️ Store Dispute in MongoDB)]

    H --> I[⏳ Dispute Status: Pending]

    I --> J[👨‍💼 Admin Dashboard]
    J --> K[🔍 Review Dispute]
    K --> L{Admin Decision}

    L -- Need More Information --> M[📋 Request Additional Details]
    M --> D

    L -- Reject --> N[❌ Dispute Rejected]
    L -- Approve --> O[✅ Dispute Approved]

    O --> P[🔄 Process Resolution]
    P --> Q[🎯 Dispute Resolved]

    N --> R[📊 Update Status]
    Q --> R

    R --> S[👤 User Tracks Dispute]
    S --> T{Resolved?}

    T -- No --> J
    T -- Yes --> U([🎉 Dispute Resolution Complete])

    style A fill:#673ab7,color:#fff,stroke:#512da8,stroke-width:2px
    style B fill:#2196f3,color:#fff,stroke:#1565c0,stroke-width:2px
    style D fill:#03a9f4,color:#fff,stroke:#0288d1,stroke-width:2px
    style E fill:#00bcd4,color:#fff,stroke:#0097a7,stroke-width:2px
    style H fill:#4caf50,color:#fff,stroke:#388e3c,stroke-width:2px
    style J fill:#ff9800,color:#fff,stroke:#f57c00,stroke-width:2px
    style K fill:#ff9800,color:#fff,stroke:#f57c00,stroke-width:2px
    style L fill:#ffc107,color:#000,stroke:#ffa000,stroke-width:2px
    style N fill:#f44336,color:#fff,stroke:#d32f2f,stroke-width:2px
    style O fill:#4caf50,color:#fff,stroke:#388e3c,stroke-width:2px
    style Q fill:#4caf50,color:#fff,stroke:#388e3c,stroke-width:2px
    style U fill:#673ab7,color:#fff,stroke:#512da8,stroke-width:2px

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

- Nayaneesh
- Pavan Sai Reddy
- Karthikeya
- Gopu Abhinav
- Team Members

---

## 📄 License

This project is developed for educational purposes.

---

## ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub.
