# MovieMateBot

**MovieMateBot** is a Telegram bot designed to simplify movie planning and tracking for pairs of users. It allows two users to create a shared movie list, categorized as "Planned" or "Watched," add movies, view lists, and get random movie suggestions from their planned list. Users connect via an invite code and interact with a unified dataset stored in Supabase.

## 📘 Project Overview

- **Name**: MovieMateBot
- **Goal**: Streamline movie watching organization for pairs
- **Platform**: Telegram bot
- **Data Storage**: Supabase (PostgreSQL)
- **Language**: Python
- **Description**: Users can link with a partner using an invite code, manage a shared movie list, and receive random movie recommendations from their planned list.

## ⚙️ Features

| Command                          | Description                                      |
|----------------------------------|--------------------------------------------------|
| `/start`                         | Initializes the user                             |
| `/invite`                        | Generates an invite code for pairing             |
| `/join <code>`                   | Joins a partner using the invite code            |
| `/add <category> <movie>`        | Adds a movie to the specified category           |
| `/list <category>`               | Displays movies in the specified category        |
| `/random`                        | Suggests a random movie from the "Planned" list  |
| `/partner_status`                | Checks if the user is paired with someone        |
| `/unlink`                        | Disconnects the user from their partner          |

## 👣 User Workflow

### 🧍 User A
1. Runs `/start`
2. Generates an invite code with `/invite` (e.g., `INV-893421`)
3. Shares the code with User B

### 🧍‍♂️ User B
1. Runs `/start`
2. Joins using `/join INV-893421`

### 🎉 Paired Users
- Add movies to shared lists
- View movies in "Planned" or "Watched" categories
- Get random movie suggestions

## 💾 Supabase Integration

### 🗃️ Database Schema

#### Table: `users`
| Column          | Type        | Description                          |
|-----------------|-------------|--------------------------------------|
| `id`            | UUID        | Unique user ID                       |
| `chat_id`       | TEXT        | Telegram chat ID                     |
| `invite_code`   | TEXT        | Invite code for pairing              |
| `partner_id`     | UUID (FK)   | Reference to the paired user         |

#### Table: `movies`
| Column        | Type            | Description                          |
|---------------|-----------------|--------------------------------------|
| `id`          | UUID            | Unique movie ID                      |
| `user_id`     | UUID (FK)       | Reference to the user                |
| `title`       | TEXT            | Movie title                          |
| `category`    | TEXT            | Category (`planned` or `watched`)    |
| `created_at`  | TIMESTAMP       | Date the movie was added             |

- `users.partner_id`: Self-referential foreign key for pairing users.
- `movies.user_id`: Links movies to their owner.

## 📦 Deployment & Technical Details

- **Bot Hosting**: Any server supporting Python
- **Supabase API**: Connects via an authorization token
- **Security**:
  - Invite codes are single-use
  - Users can only have one partner at a time

## 📈 Future Enhancements

- AI-powered movie recommendations
- Support for groups larger than two users
- Movie watch reminders
- Integration with TMDB API for movie details and posters

## 📜 License

This project is licensed under the MIT License. See the LICENSE file for details.

Built with ❤️ by ValliKaz