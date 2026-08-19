# 💳 UPI Dispute Management System

<p align="center">
  <img src="https://img.shields.io/badge/Project-UPI%20Dispute%20Management-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Backend-API-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Database-MySQL-blue?style=for-the-badge" />
</p>

<p align="center">
  <b>A smart platform for raising, tracking, reviewing, and resolving UPI payment disputes.</b>
</p>

---

## 📌 Overview

The **UPI Dispute Management System** is a web-based application designed to simplify the process of handling UPI payment disputes.

Users can raise disputes for failed, pending, or unauthorized transactions and track the status of their complaints.

Administrators can review disputes, verify transaction details, update dispute status, and manage the complete resolution process.

The system provides a structured workflow that improves transparency, reduces manual processing, and makes dispute resolution easier.

---

# 🎯 Objectives

The main objectives of this project are:

- 🔹 Allow users to raise UPI payment disputes.
- 🔹 Store and manage dispute information securely.
- 🔹 Allow users to track their dispute status.
- 🔹 Provide administrators with a centralized dispute dashboard.
- 🔹 Simplify dispute verification and resolution.
- 🔹 Maintain transaction and dispute history.
- 🔹 Improve transparency between users and administrators.

---

# ✨ Key Features

## 👤 User Module

- 🔐 User Registration & Login
- 💳 Submit UPI Transaction Dispute
- 📝 Enter Transaction Details
- 📎 Upload Supporting Information
- 🔍 Track Dispute Status
- 📜 View Dispute History
- 🔔 Receive Status Updates

---

## 👨‍💼 Admin Module

- 🔐 Admin Authentication
- 📊 Admin Dashboard
- 📋 View All Disputes
- 🔎 Search and Filter Disputes
- ✅ Verify Dispute Details
- 🔄 Update Dispute Status
- 🛠️ Resolve or Reject Disputes
- 📜 View Complete Dispute History

---

# 🔄 System Workflow

The complete workflow of the system is:

```text
                    ┌──────────────────┐
                    │      USER        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Register / Login │
                    └────────┬─────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ UPI Transaction      │
                  │ Dispute Submission  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Validate Transaction │
                  │ & Dispute Details   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Store Dispute in DB  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Admin Dashboard    │
                  └──────────┬───────────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
             ┌───────┐  ┌────────┐  ┌────────┐
             │Review │  │Verify  │  │Search  │
             │Dispute│  │Details │  │Dispute │
             └───┬───┘  └───┬────┘  └────────┘
                 │            │
                 └──────┬─────┘
                        ▼
              ┌────────────────────┐
              │ Update Dispute     │
              │ Status             │
              └─────────┬──────────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          ┌──────┐  ┌────────┐  ┌─────────┐
          │Pending│ │Resolved│  │Rejected │
          └───┬───┘  └───┬────┘  └────┬────┘
              │          │             │
              └──────────┼─────────────┘
                         ▼
                 ┌────────────────┐
                 │ User Tracks    │
                 │ Final Status   │
                 └────────────────┘
