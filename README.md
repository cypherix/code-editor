
# 🖥️ CodeHUB

An online collaborative code editor where users can create files and folders, store code without running it, and experience real-time collaboration! 🚀

> **Note**: This app is currently under development! Stay tuned for more updates. 👨‍💻👩‍💻

## 🌟 Features

- 🗂️ **File & Folder Management**: Create and organize files and folders.
- 🔗 **Unique Slug for Every Project**: Each project gets a unique URL (slug) that can be shared with others.
- 👥 **Real-time Collaboration**: Watch changes live as they happen between users on the same slug.
- 📝 **Monaco Editor Integration**: Write and edit code using the powerful Monaco editor (VS Code's underlying editor).
- 🛠️ **Persistent Storage**: All changes are saved in the cloud so you never lose your work!

## 🚀 Tech Stack

### Frontend
- **Framework**: Next.js
- **Editor**: Monaco Editor
- **State Management**: Zustand
- **UI**: Chakra UI
- **Real-time Updates**: WebSocket (Socket.IO)

### Backend
- **Runtime**: Node.js
- **Framework**: Express.js 
- **Database**: MongoDB
- **Real-time Sync**: Operational Transformation (OT) or Conflict-Free Replicated Data Types (CRDT)
- **File Storage**: AWS S3 

### Architecture
1. Users create a project with files and folders 🗂️.
2. Each project is assigned a unique slug 🔗.
3. Multiple users can access the slug and make changes in real-time 📝.
4. Changes are synced across users using WebSocket 🚦.
5. All data is persisted in the database 📂.

## ⚡ How It Works

1. Visit a slug URL like `/exampleSlug` 🔗.
2. Create or edit files and folders in the Monaco editor 💻.
3. If someone else joins the same slug, they’ll see your changes in real-time 🔄.
4. Your work is auto-saved and persisted, so you never lose it! 💾

## 🔧 Installation (Development Mode)

```bash
# Clone the repository
git clone https://github.com/username/codecollab.git

# Install dependencies
npm install

# Start the development server
npm run dev
```

## 👨‍💻 Contribution Guidelines

We welcome contributions! Please follow these steps:

1. Fork the repo 🍴.
2. Create a new branch for your feature or bugfix 🌿.
3. Submit a pull request 🔄.

## 📅 What's Next?

- 🚧 Real-time collaboration with Operational Transformation (OT) or CRDT.
- 🔒 User authentication and project permissions.
- 💾 Autosaving and versioning.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

⚠️ **Note**: This project is under active development. Some features might not be fully functional yet. Stay tuned! 🌱
