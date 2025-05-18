# MovieMate Telegram Bot

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

## 📊 ER Diagram

```mermaid
erDiagram
    USERS ||--o{ MOVIES : "owns"
    USERS ||--o| USERS : "paired_with"
    USERS {
        UUID id PK
        TEXT chat_id
        TEXT invite_code
        UUID partner_id FK
    }
    MOVIES {
        UUID id PK
        UUID user_id FK
        TEXT title
        TEXT category
        TIMESTAMP created_at
    }
```

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

## 🆕 Advanced Features (2025)

- **Full button-based interface**: All actions (add, edit, delete, change category, random pick) are available via Telegram buttons and menus — no need to remember commands.
- **Edit movie title and category**: Change both the name and the category (planned/loved) of any movie via interactive inline menus.
- **Delete with confirmation**: Deleting a movie always asks for confirmation via Yes/No buttons.
- **Unified edit menu**: The "Edit Movies" menu allows you to:
  - Edit movie title (choose a movie, then enter a new name)
  - Change movie category (choose a movie, then select category)
  - Delete a movie (choose a movie, then confirm)
- **Robust error handling**: All user actions and errors are logged; the bot provides clear feedback for every operation.
- **Partner-aware**: All lists and actions are always synchronized between you and your paired user.

## 📝 Example Usage (Button Flow)

1. Open the main menu and tap "✏️ Edit Movies" (or use `/editdeletemenu`).
2. See your full movie list and choose:
   - "✏️ Edit Title" — select a movie, then enter a new title.
   - "🗂️ Edit Category" — select a movie, then pick Planned/Loved.
   - "🗑️ Delete" — select a movie, then confirm deletion.
3. All changes are instantly reflected for both you and your partner.

## 🛠️ Tech Stack
- Python 3.10+
- python-telegram-bot
- Supabase (PostgreSQL)
- dotenv
- Logging to file and console

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ValliKaz/MovieMatebot.git
cd MovieMateBot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# For Windows:
venv\Scripts\activate
# For Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root, add your bot token and since I'm using Supabase, add your Supabase URL and key:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

## Running the Bot

```bash
python bot.py
```

## 📜 License

This project is licensed under the MIT License.

Built with ❤️ by ValliKaz