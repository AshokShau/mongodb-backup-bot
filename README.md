# MongoDB Backup Bot 📦

A Telegram bot built using [PyTDBot](https://github.com/pytdbot/client) to backup and restore MongoDB databases.

<p align="center">
  <!-- GitHub Stars -->
  <a href="https://github.com/AshokShau/TgMongoBot/stargazers">
    <img src="https://img.shields.io/github/stars/AshokShau/TgMongoBot?style=for-the-badge&color=black&logo=github" alt="Stars"/>
  </a>
  
  <!-- GitHub Forks -->
  <a href="https://github.com/AshokShau/TgMongoBot/network/members">
    <img src="https://img.shields.io/github/forks/AshokShau/TgMongoBot?style=for-the-badge&color=black&logo=github" alt="Forks"/>
  </a>

  <!-- Last Commit -->
  <a href="https://github.com/AshokShau/TgMongoBot/commits/AshokShau">
    <img src="https://img.shields.io/github/last-commit/AshokShau/TgMongoBot?style=for-the-badge&color=blue" alt="Last Commit"/>
  </a>

  <!-- Repo Size -->
  <a href="https://github.com/AshokShau/TgMongoBot">
    <img src="https://img.shields.io/github/repo-size/AshokShau/TgMongoBot?style=for-the-badge&color=success" alt="Repo Size"/>
  </a>

  <!-- Language -->
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Written%20in-Python-orange?style=for-the-badge&logo=python" alt="Python"/>
  </a>

  <!-- License -->
  <a href="https://github.com/AshokShau/TgMongoBot/blob/AshokShau/LICENSE">
    <img src="https://img.shields.io/github/license/AshokShau/TgMongoBot?style=for-the-badge&color=blue" alt="License"/>
  </a>

  <!-- Open Issues -->
  <a href="https://github.com/AshokShau/TgMongoBot/issues">
    <img src="https://img.shields.io/github/issues/AshokShau/TgMongoBot?style=for-the-badge&color=red" alt="Issues"/>
  </a>

  <!-- Pull Requests -->
  <a href="https://github.com/AshokShau/TgMongoBot/pulls">
    <img src="https://img.shields.io/github/issues-pr/AshokShau/TgMongoBot?style=for-the-badge&color=purple" alt="PRs"/>
  </a>

  <!-- GitHub Workflow CI -->
  <a href="https://github.com/AshokShau/TgMongoBot/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/AshokShau/TgMongoBot/code-fixer.yml?style=for-the-badge&label=CI&logo=github" alt="CI Status"/>
  </a>
</p>

## Features

- 🔐 Backup MongoDB databases via `/mongo <URI>`
- 💾 Supports `.gz` (default) and `.json` formats
- 📥 Import backups by replying to a file with `/mongo {import} <URI>`
- 🐳 Docker-ready with pre-installed MongoDB tools
- ⚡ Fully asynchronous and lightweight

## Commands

- `/mongo <mongodb_uri>` — Create a `.gz` backup
- `/mongo {json} <mongodb_uri>` — Create a `.json` backup
- `/mongo {import} <mongodb_uri>` — Restore by replying to a `.gz` or `.json` backup
