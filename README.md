# 🌊 Floatly

**Digital Logbook for Mobile Money Agents in Cameroon**

Floatly replaces paper notebooks to track transactions, cash, and digital float for MTN MoMo and Orange Money agents.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd floatly
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Open in browser**
   - Home: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/
   - Health Check: http://127.0.0.1:8000/health/

---

## 📦 Tech Stack

### Backend
| Package | Purpose |
|---------|---------|
| **Django 6.0** | Web framework |
| **django-environ** | Environment variable management |
| **whitenoise** | Efficient static file serving |
| **pillow** | Image processing (receipt photos) |
| **django-extensions** | Developer utilities |

### Frontend
| Technology | Purpose |
|------------|---------|
| **TailwindCSS** | Utility-first CSS framework |
| **HTMX** | Dynamic updates without page refresh |
| **AlpineJS** | Lightweight JavaScript interactivity |
| **Inter Font** | Modern, readable typography |

### Forms & UI
| Package | Purpose |
|---------|---------|
| **django-crispy-forms** | Better form rendering |
| **crispy-tailwind** | Tailwind styling for forms |
| **django-compressor** | CSS/JS compression |

### PWA & Notifications
| Package | Purpose |
|---------|---------|
| **django-pwa** | Progressive Web App support |
| **pywebpush** | Web push notifications |

---

## 📁 Project Structure

```
floatly/
├── config/                 # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI application
├── core/                   # Main application
│   ├── templates/
│   │   └── core/          # Core app templates
│   ├── models.py          # Database models
│   ├── views.py           # View functions
│   └── urls.py            # App URL patterns
├── templates/              # Global templates
│   └── base.html          # Base template
├── static/                 # Static files
│   ├── css/               # Stylesheets
│   ├── js/                # JavaScript
│   │   └── serviceworker.js
│   └── images/            # Images & icons
├── media/                  # User uploads
│   └── receipts/          # Transaction receipts
├── .env                    # Environment variables
├── .env.example            # Example env file
├── requirements.txt        # Python dependencies
└── manage.py              # Django CLI
```

---

## ✅ Feature Checklist

### Phase 1: Foundation
- [x] Django project setup
- [x] TailwindCSS + HTMX + AlpineJS integration
- [x] Base templates with modern UI
- [x] Health check endpoint
- [x] PWA service worker (offline support)
- [ ] User authentication

### Phase 2: Core Features
- [ ] Kiosk management
- [ ] Transaction logging
- [ ] Auto-profit calculator
- [ ] Balance tracking (Cash/Float)

### Phase 3: Advanced Features
- [ ] Multi-kiosk support
- [ ] Member invitations
- [ ] Notification center
- [ ] Push notifications
- [ ] Daily summaries

---

## 🔧 Health Check

Access `/health/` to verify system status:

```json
{
  "status": "ok",
  "service": "Floatly",
  "version": "1.0.0",
  "database": "healthy",
  "features": {
    "transactions": "pending",
    "kiosks": "pending",
    "notifications": "pending",
    "auto_profit": "pending"
  }
}
```

---

## 🎨 Design System

### Colors
- **Primary**: Blue shades for trust and professionalism
- **Accent**: Purple for premium features
- **MoMo MTN**: `#ffcc00` (Yellow)
- **Orange Money**: `#ff6600` (Orange)

### Typography
- **Font**: Inter (Google Fonts)
- **Weights**: 300-800

---

## 📱 PWA Features

Floatly is a Progressive Web App that:
- Works offline
- Can be installed on home screen
- Sends push notifications
- Syncs data when back online

---

## 🔐 Security

- CSRF protection enabled
- Secure session handling
- Password validation
- Production-ready security headers

---

## 📄 License

Copyright © 2024 Floatly. Built for Cameroon's mobile money agents.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request
